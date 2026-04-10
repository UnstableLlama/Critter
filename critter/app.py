"""
Critter GTK4 Application.
Wires together hook servers, proxy servers, session store, buddy system, and UI.
Supports Claude Code hooks, Codex hooks, and transparent API proxies.
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
from .codex_hook_installer import install_if_needed as install_codex_hooks
from .config import CritterConfig, detect_local_backends
from .hook_installer import install_if_needed as install_claude_hooks
from .hook_server import HookSocketServer
from .providers import get_provider
from .providers.base import StreamEvent
from .proxy import ProxyServer
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
        self._proxies: list[ProxyServer] = []
        self._config: CritterConfig | None = None
        self._window: MainWindow | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None

    def _on_activate(self, app):
        if self._window:
            self._window.present()
            return

        # Load configuration
        self._config = CritterConfig.load()
        CritterConfig.create_default_config()

        # Install Claude Code hooks
        if self._config.claude_code_hooks:
            try:
                install_claude_hooks()
                logger.info("Claude Code hooks installed/verified")
            except Exception:
                logger.exception("Failed to install Claude Code hooks")

        # Install Codex hooks
        if self._config.codex_hooks:
            try:
                install_codex_hooks()
                logger.info("Codex hooks installed/verified")
            except Exception:
                logger.exception("Failed to install Codex hooks")

        # Create window
        self._window = MainWindow(
            app=self,
            identity=self._identity,
            on_approve=self._approve_session,
            on_deny=self._deny_session,
        )
        self._window.present()
        self._window.start_animation()

        # Wire up store -> UI updates
        self._store.set_on_change(self._schedule_ui_update)

        # Start async event loop in background thread
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_async_loop, daemon=True
        )
        self._loop_thread.start()

        # Start the Unix socket server for hooks
        asyncio.run_coroutine_threadsafe(
            self._server.start(on_event=self._on_hook_event), self._loop
        )

        # Start proxy servers for configured backends
        self._start_proxies()

        # Auto-detect local backends not already configured
        self._auto_detect_backends()

        logger.info(
            "Critter started - buddy: %s %s (%s) - %d backend(s) configured",
            self._identity.species.value,
            self._identity.eye.display_name,
            self._identity.rarity.value,
            len(self._proxies),
        )

    def _start_proxies(self):
        """Start proxy servers for all enabled backends in config."""
        if not self._config:
            return

        for backend in self._config.backends:
            if not backend.enabled or not backend.url:
                continue
            self._start_proxy(
                backend.name, backend.url, backend.provider, backend.proxy_port
            )

    def _auto_detect_backends(self):
        """Detect local LLM services and start proxies for them."""
        # Get names of already-configured backends to avoid duplicates
        configured_names = set()
        if self._config:
            configured_names = {b.name for b in self._config.backends if b.enabled}

        for backend in detect_local_backends():
            if backend.name not in configured_names:
                logger.info(
                    "Auto-detected %s at %s, proxying on port %d",
                    backend.name, backend.url, backend.proxy_port,
                )
                self._start_proxy(
                    backend.name, backend.url, backend.provider, backend.proxy_port
                )

    def _start_proxy(
        self, name: str, url: str, provider_name: str, port: int
    ):
        """Create and start a single proxy server."""
        try:
            provider = get_provider(provider_name)
        except ValueError:
            logger.error("Unknown provider %s for backend %s", provider_name, name)
            return

        proxy = ProxyServer(
            backend_name=name,
            backend_url=url,
            provider=provider,
            listen_port=port,
            on_event=self._on_proxy_event,
        )
        self._proxies.append(proxy)
        asyncio.run_coroutine_threadsafe(proxy.start(), self._loop)

    def _on_shutdown(self, app):
        if self._window:
            self._window.stop_animation()

        if self._loop:
            # Stop hook server
            asyncio.run_coroutine_threadsafe(self._server.stop(), self._loop)
            # Stop all proxies
            for proxy in self._proxies:
                asyncio.run_coroutine_threadsafe(proxy.stop(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _on_hook_event(self, event: HookEvent):
        """Called from the async thread when a hook event arrives."""
        self._store.process_hook(event)

        if event.event == "Stop":
            self._server.cancel_pending(event.session_id)

        if event.event == "PostToolUse" and event.tool_use_id:
            self._server.cancel_specific(event.tool_use_id)

    def _on_proxy_event(
        self, session_id: str, backend_name: str, event: StreamEvent
    ):
        """Called from the async thread when a proxy stream event arrives."""
        self._store.process_proxy_event(session_id, backend_name, event)

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
