"""
Main application window.
Combines the buddy view, session list, and controls.
"""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Adw, Pango

from ..buddy.identity import BuddyIdentity, Task
from ..session_state import PhaseKind, SessionState
from .buddy_view import BuddyView
from .session_view import SessionListView

CSS = """
.buddy-sprite {
    padding: 8px;
}

.buddy-name {
    font-size: 13px;
}

.buddy-rarity {
    font-size: 16px;
    color: @warning_color;
}

.buddy-status {
    opacity: 0.7;
}

.session-row {
    padding: 12px;
    border-radius: 8px;
}

.session-title {
    font-size: 14px;
}

.dim-label {
    opacity: 0.55;
    font-size: 11px;
}

.processing-label {
    color: @accent_color;
    font-weight: bold;
    font-size: 11px;
}

.waiting-label {
    color: @success_color;
    font-weight: bold;
    font-size: 11px;
}

.approval-label {
    color: @warning_color;
    font-weight: bold;
    font-size: 11px;
}

.header-bar-title {
    font-weight: bold;
}

.status-bar {
    padding: 6px 12px;
    font-size: 11px;
}
"""


class MainWindow(Gtk.ApplicationWindow):
    """The main Critter window."""

    def __init__(
        self,
        app: Gtk.Application,
        identity: BuddyIdentity,
        on_approve: Callable[[str], None],
        on_deny: Callable[[str], None],
    ):
        super().__init__(application=app, title="Critter")
        self.set_default_size(420, 680)

        self._on_approve = on_approve
        self._on_deny = on_deny

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Main layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(vbox)

        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        title_label = Gtk.Label(label="Critter")
        title_label.get_style_context().add_class("header-bar-title")
        header.set_title_widget(title_label)
        self.set_titlebar(header)

        # Buddy display area
        buddy_frame = Gtk.Frame()
        buddy_frame.set_margin_start(12)
        buddy_frame.set_margin_end(12)
        buddy_frame.set_margin_top(12)
        self._buddy_view = BuddyView(identity)
        self._buddy_view.set_margin_top(16)
        self._buddy_view.set_margin_bottom(16)
        buddy_frame.set_child(self._buddy_view)
        vbox.append(buddy_frame)

        # Sessions header
        sessions_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        sessions_header.set_margin_start(12)
        sessions_header.set_margin_end(12)
        sessions_header.set_margin_top(12)
        sessions_header.set_margin_bottom(4)

        sessions_title = Gtk.Label(label="Sessions")
        sessions_title.set_xalign(0)
        sessions_title.set_hexpand(True)
        font_bold = Pango.AttrList.new()
        font_bold.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        sessions_title.set_attributes(font_bold)
        sessions_header.append(sessions_title)

        self._session_count = Gtk.Label(label="0")
        self._session_count.get_style_context().add_class("dim-label")
        sessions_header.append(self._session_count)

        vbox.append(sessions_header)

        # Session list
        self._session_list = SessionListView(
            on_approve=on_approve, on_deny=on_deny
        )
        self._session_list.set_margin_start(12)
        self._session_list.set_margin_end(12)
        self._session_list.set_margin_bottom(12)
        vbox.append(self._session_list)

        # Status bar
        self._status_bar = Gtk.Label(label="Listening for Claude Code sessions...")
        self._status_bar.set_xalign(0)
        self._status_bar.get_style_context().add_class("status-bar")
        self._status_bar.get_style_context().add_class("dim-label")
        vbox.append(self._status_bar)

    def start_animation(self):
        self._buddy_view.start()

    def stop_animation(self):
        self._buddy_view.stop()

    def update_sessions(self, sessions: list[SessionState]):
        """Update the session list and buddy state from new data."""
        self._session_list.update_sessions(sessions)
        self._session_count.set_text(str(len(sessions)))

        # Update buddy task based on most active session
        task = self._derive_buddy_task(sessions)
        self._buddy_view.set_task(task)

        # Update status bar
        if not sessions:
            self._status_bar.set_text("Listening for Claude Code sessions...")
        else:
            pending = sum(1 for s in sessions if s.needs_attention)
            if pending:
                self._status_bar.set_text(
                    f"{len(sessions)} session(s) - {pending} need attention"
                )
            else:
                self._status_bar.set_text(f"{len(sessions)} active session(s)")

    def _derive_buddy_task(self, sessions: list[SessionState]) -> Task:
        """Map session states to buddy animation task."""
        if not sessions:
            return Task.SLEEPING

        for s in sessions:
            if s.phase.kind == PhaseKind.WAITING_FOR_APPROVAL:
                return Task.WAITING
        for s in sessions:
            if s.phase.kind == PhaseKind.PROCESSING:
                return Task.WORKING
        for s in sessions:
            if s.phase.kind == PhaseKind.COMPACTING:
                return Task.READING
        for s in sessions:
            if s.phase.kind == PhaseKind.WAITING_FOR_INPUT:
                return Task.IDLE

        return Task.IDLE
