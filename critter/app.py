"""
Critter GTK4 Application.
Wires together the hook server, session store, buddy system, and UI.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Adw

from .buddy.detector import detect as detect_buddy
from .hook_installer import install_if_needed
from .hook_server import HookSocketServer
from .session_state import HookEvent
from .session_store import SessionStore
from .ui.main_window import MainWindow

logger = logging.getLogger("critter")


class CritterApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.critter.app")
        self.connect("activate", self._on_activate)
        self.connect("shutdown", self._on_shutdown)

        self._identity = detect_buddy()
        self._store = SessionStore()
        self._server = HookSocketServer()
        self._window: MainWindow | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None

    def _on_activate(self, app):
        if self._window:
            self._window.present()
            return

        # Install hooks
        try:
            install_if_needed()
            logger.info("Hooks installed/verified")
        except Exception:
            logger.exception("Failed to install hooks")

        # Create window
        self._window = MainWindow(
            app=self,
            identity=self._identity,
            on_approve=self._approve_session,
            on_deny=self._deny_session,
        )
        self._window.present()
        self._window.start_animation()

        # Wire up store → UI updates
        self._store.set_on_change(self._schedule_ui_update)

        # Start async event loop in background thread
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_async_loop, daemon=True
        )
        self._loop_thread.start()

        # Start the socket server
        asyncio.run_coroutine_threadsafe(
            self._server.start(on_event=self._on_hook_event), self._loop
        )

        logger.info(
            "Critter started - buddy: %s %s (%s)",
            self._identity.species.value,
            self._identity.eye.display_name,
            self._identity.rarity.value,
        )

    def _on_shutdown(self, app):
        if self._window:
            self._window.stop_animation()

        if self._loop:
            asyncio.run_coroutine_threadsafe(self._server.stop(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _on_hook_event(self, event: HookEvent):
        """Called from the async thread when a hook event arrives."""
        # Process in store (thread-safe since store is simple dict ops)
        self._store.process_hook(event)

        # Handle Stop → cancel pending permissions
        if event.event == "Stop":
            self._server.cancel_pending(event.session_id)

        # Handle PostToolUse → cancel specific pending permission
        if event.event == "PostToolUse" and event.tool_use_id:
            self._server.cancel_specific(event.tool_use_id)

    def _schedule_ui_update(self):
        """Schedule a UI update on the GTK main thread."""
        GLib.idle_add(self._update_ui)

    def _update_ui(self) -> bool:
        if self._window:
            self._window.update_sessions(self._store.sessions)
        return False  # run once

    def _approve_session(self, session_id: str):
        session = self._store.session(session_id)
        if not session or not session.active_permission:
            return

        tool_use_id = session.active_permission.tool_use_id
        self._server.respond_to_permission(tool_use_id, "allow")
        self._store.process_permission_approved(session_id, tool_use_id)

    def _deny_session(self, session_id: str):
        session = self._store.session(session_id)
        if not session or not session.active_permission:
            return

        tool_use_id = session.active_permission.tool_use_id
        self._server.respond_to_permission(tool_use_id, "deny", "Denied via Critter")
        self._store.process_permission_denied(session_id, tool_use_id)


def run():
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    app = CritterApp()

    # Let Ctrl+C work
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, app.quit)

    app.run(None)
