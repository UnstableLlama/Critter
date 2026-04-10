"""
Session list and detail view.
Shows all active Claude Code sessions with their status and permission controls.
"""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, GLib

from ..session_state import PhaseKind, SessionSource, SessionState


# Phase → display info
_PHASE_DISPLAY: dict[PhaseKind, tuple[str, str]] = {
    PhaseKind.IDLE: ("Idle", "dim-label"),
    PhaseKind.PROCESSING: ("Processing...", "processing-label"),
    PhaseKind.WAITING_FOR_INPUT: ("Waiting for input", "waiting-label"),
    PhaseKind.WAITING_FOR_APPROVAL: ("Needs approval", "approval-label"),
    PhaseKind.COMPACTING: ("Compacting...", "processing-label"),
    PhaseKind.ENDED: ("Ended", "dim-label"),
}


class SessionRow(Gtk.Box):
    """A single session row with status, project name, and action buttons."""

    def __init__(
        self,
        session: SessionState,
        on_approve: Callable[[str], None],
        on_deny: Callable[[str], None],
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.get_style_context().add_class("session-row")

        self._session_id = session.session_id
        self._on_approve = on_approve
        self._on_deny = on_deny

        # Header row: project name + phase
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_hexpand(True)

        # Source badge
        source_label = Gtk.Label(label=session.source_label)
        source_label.get_style_context().add_class("dim-label")
        header.append(source_label)

        title = Gtk.Label(label=session.display_title)
        title.set_xalign(0)
        title.set_hexpand(True)
        title.get_style_context().add_class("session-title")
        font_bold = Pango.AttrList.new()
        font_bold.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        title.set_attributes(font_bold)
        header.append(title)

        display_text, css_class = _PHASE_DISPLAY.get(
            session.phase.kind, ("Unknown", "dim-label")
        )
        phase_label = Gtk.Label(label=display_text)
        phase_label.get_style_context().add_class(css_class)
        header.append(phase_label)

        self.append(header)

        # Info row: cwd + pid (hook sessions) or model (proxy sessions)
        info_parts = []
        if session.cwd:
            info_parts.append(session.cwd)
        if session.pid:
            info_parts.append(f"PID {session.pid}")
        if session.tty:
            info_parts.append(session.tty)
        if session.model:
            info_parts.append(session.model)
        info_text = "  |  ".join(info_parts) if info_parts else session.source_label

        info = Gtk.Label(label=info_text)
        info.set_xalign(0)
        info.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        info.get_style_context().add_class("dim-label")
        self.append(info)

        # Permission section (only if waiting for approval)
        perm = session.active_permission
        if perm:
            sep = Gtk.Separator()
            self.append(sep)

            tool_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            tool_box.set_margin_top(4)

            tool_label = Gtk.Label()
            tool_label.set_xalign(0)
            tool_label.set_markup(f"<b>Tool:</b> {GLib.markup_escape_text(perm.tool_name)}")
            tool_box.append(tool_label)

            if perm.formatted_input:
                input_label = Gtk.Label()
                input_label.set_xalign(0)
                input_label.set_wrap(True)
                input_label.set_selectable(True)
                input_label.set_max_width_chars(60)
                font_mono = Pango.AttrList.new()
                font_mono.insert(
                    Pango.attr_font_desc_new(
                        Pango.FontDescription.from_string("monospace 9")
                    )
                )
                input_label.set_attributes(font_mono)
                # Truncate very long inputs
                text = perm.formatted_input
                if len(text) > 500:
                    text = text[:500] + "\n..."
                input_label.set_text(text)
                tool_box.append(input_label)

            self.append(tool_box)

            # Approve / Deny buttons
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            btn_box.set_margin_top(8)
            btn_box.set_halign(Gtk.Align.END)

            deny_btn = Gtk.Button(label="Deny")
            deny_btn.get_style_context().add_class("destructive-action")
            deny_btn.connect("clicked", self._on_deny_clicked)
            btn_box.append(deny_btn)

            approve_btn = Gtk.Button(label="Approve")
            approve_btn.get_style_context().add_class("suggested-action")
            approve_btn.connect("clicked", self._on_approve_clicked)
            btn_box.append(approve_btn)

            self.append(btn_box)

    def _on_approve_clicked(self, _btn):
        self._on_approve(self._session_id)

    def _on_deny_clicked(self, _btn):
        self._on_deny(self._session_id)


class SessionListView(Gtk.ScrolledWindow):
    """Scrollable list of all active sessions."""

    def __init__(
        self,
        on_approve: Callable[[str], None],
        on_deny: Callable[[str], None],
    ):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_min_content_height(150)

        self._on_approve = on_approve
        self._on_deny = on_deny

        self._list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(self._list_box)

        self._empty_label = Gtk.Label(
            label="No active sessions\n\nStart Claude Code, Codex, or an API request\nthrough a proxy and it will appear here."
        )
        self._empty_label.set_justify(Gtk.Justification.CENTER)
        self._empty_label.get_style_context().add_class("dim-label")
        self._empty_label.set_margin_top(40)
        self._list_box.append(self._empty_label)

    def update_sessions(self, sessions: list[SessionState]):
        # Clear existing children
        child = self._list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._list_box.remove(child)
            child = next_child

        if not sessions:
            self._list_box.append(self._empty_label)
            return

        for i, session in enumerate(sessions):
            if i > 0:
                self._list_box.append(Gtk.Separator())
            row = SessionRow(session, self._on_approve, self._on_deny)
            self._list_box.append(row)
