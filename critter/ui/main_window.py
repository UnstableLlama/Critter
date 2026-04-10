"""
Main application window.
Combines the buddy view, session list, controls, and journal.
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Adw, Pango

from ..buddy.growth import GrowthStage
from ..buddy.identity import BuddyIdentity, Task
from ..buddy.mood import Mood
from ..buddy.stats import CritterStats
from ..session_state import PhaseKind, SessionSource, SessionState
from .buddy_view import BuddyView
from .session_view import SessionListView

if TYPE_CHECKING:
    from ..buddy.journal import Journal

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

.stats-display {
    opacity: 0.8;
    padding: 4px 8px;
}

.reaction-label {
    color: @accent_color;
    font-weight: bold;
    min-height: 20px;
}

.tamagotchi-btn {
    min-width: 55px;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 11px;
}

.needs-attention {
    background: alpha(@warning_color, 0.2);
    border-color: @warning_color;
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

.milestone-label {
    color: @warning_color;
    font-weight: bold;
    font-size: 12px;
    padding: 4px 12px;
}
"""


class MainWindow(Gtk.ApplicationWindow):
    """The main Critter window - tamagotchi-style companion."""

    def __init__(
        self,
        app: Gtk.Application,
        identity: BuddyIdentity,
        on_approve: Callable[[str], None],
        on_deny: Callable[[str], None],
        on_feed: Callable[[], None] | None = None,
        on_play: Callable[[], None] | None = None,
        on_rest: Callable[[], None] | None = None,
        on_pet: Callable[[], None] | None = None,
        journal: "Journal | None" = None,
    ):
        super().__init__(application=app, title="Critter")
        self.set_default_size(420, 720)

        self._on_approve = on_approve
        self._on_deny = on_deny
        self._journal = journal

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

        # Diary button in header
        if journal:
            diary_btn = Gtk.Button(label="Diary")
            diary_btn.connect("clicked", self._on_diary_clicked)
            header.pack_end(diary_btn)

        self.set_titlebar(header)

        # Buddy display area
        buddy_frame = Gtk.Frame()
        buddy_frame.set_margin_start(12)
        buddy_frame.set_margin_end(12)
        buddy_frame.set_margin_top(8)
        self._buddy_view = BuddyView(
            identity,
            on_feed=on_feed,
            on_play=on_play,
            on_rest=on_rest,
            on_pet=on_pet,
        )
        self._buddy_view.set_margin_top(12)
        self._buddy_view.set_margin_bottom(8)
        buddy_frame.set_child(self._buddy_view)
        vbox.append(buddy_frame)

        # Milestone notification (hidden by default)
        self._milestone_label = Gtk.Label(label="")
        self._milestone_label.get_style_context().add_class("milestone-label")
        self._milestone_label.set_visible(False)
        vbox.append(self._milestone_label)

        # Sessions header
        sessions_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        sessions_header.set_margin_start(12)
        sessions_header.set_margin_end(12)
        sessions_header.set_margin_top(8)
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
        self._status_bar = Gtk.Label(label="Listening for sessions...")
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
            self._status_bar.set_text("Listening for sessions...")
        else:
            pending = sum(1 for s in sessions if s.needs_attention)
            sources = set(s.source_label for s in sessions)
            source_str = ", ".join(sorted(sources))
            if pending:
                self._status_bar.set_text(
                    f"{len(sessions)} session(s) [{source_str}] - "
                    f"{pending} need attention"
                )
            else:
                self._status_bar.set_text(
                    f"{len(sessions)} session(s) [{source_str}]"
                )

    def update_mood(self, mood: Mood):
        """Update the buddy's displayed mood."""
        self._buddy_view.set_mood(mood)

    def update_stats(self, stats: CritterStats):
        """Update the stat bars display."""
        self._buddy_view.update_stats(stats)

    def show_reaction(self, text: str):
        """Show a brief reaction from a button press."""
        self._buddy_view.show_reaction(text)

    def update_growth(self, stage: GrowthStage):
        """Update the growth stage display."""
        self._buddy_view.set_growth_stage(stage)

    def show_milestone(self, text: str):
        """Flash a milestone notification."""
        self._milestone_label.set_text(text)
        self._milestone_label.set_visible(True)
        GLib.timeout_add(5000, self._hide_milestone)

    def _hide_milestone(self) -> bool:
        self._milestone_label.set_visible(False)
        return False

    def _on_diary_clicked(self, _btn):
        """Open the journal popover."""
        if not self._journal:
            return
        from .journal_view import JournalPopover

        popover = JournalPopover(self._journal)
        popover.set_parent(_btn)
        popover.popup()

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
