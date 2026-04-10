"""
Journal view - a popover showing the critter's diary entries.
The critter writes about its day from its own perspective.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, GLib

if TYPE_CHECKING:
    from ..buddy.journal import Journal


class JournalPopover(Gtk.Popover):
    """Shows recent journal entries in a scrollable popover."""

    def __init__(self, journal: Journal):
        super().__init__()
        self._journal = journal
        self.set_size_request(360, 400)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)

        # Header
        header = Gtk.Label(label="Critter's Diary")
        header.set_xalign(0)
        bold = Pango.AttrList.new()
        bold.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        header.set_attributes(bold)
        vbox.append(header)

        sep = Gtk.Separator()
        vbox.append(sep)

        # Scrollable entry list
        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_min_content_height(300)

        self._entries_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        scroll.set_child(self._entries_box)
        vbox.append(scroll)

        # Entry count
        self._count_label = Gtk.Label()
        self._count_label.set_xalign(1)
        self._count_label.get_style_context().add_class("dim-label")
        vbox.append(self._count_label)

        self.set_child(vbox)
        self._refresh()

    def _refresh(self):
        """Rebuild the entry list from the journal."""
        # Clear
        child = self._entries_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._entries_box.remove(child)
            child = next_child

        entries = self._journal.recent
        if not entries:
            empty = Gtk.Label(
                label="No diary entries yet.\n\nYour critter will start writing\nas you use it together!"
            )
            empty.set_justify(Gtk.Justification.CENTER)
            empty.get_style_context().add_class("dim-label")
            empty.set_margin_top(40)
            self._entries_box.append(empty)
            self._count_label.set_text("")
            return

        # Show entries newest-first
        for entry in reversed(entries):
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row.set_margin_bottom(6)

            # Time + mood
            time_str = entry.formatted_time
            date_str = entry.formatted_date
            meta = Gtk.Label(label=f"{date_str} {time_str}")
            meta.set_xalign(0)
            meta.get_style_context().add_class("dim-label")
            row.append(meta)

            # Entry text
            text = Gtk.Label(label=entry.text)
            text.set_xalign(0)
            text.set_wrap(True)
            text.set_max_width_chars(45)
            text.set_selectable(True)

            # Use slightly smaller font
            font_attrs = Pango.AttrList.new()
            font_attrs.insert(
                Pango.attr_font_desc_new(
                    Pango.FontDescription.from_string("9")
                )
            )
            text.set_attributes(font_attrs)
            row.append(text)

            self._entries_box.append(row)

            # Separator between entries
            self._entries_box.append(Gtk.Separator())

        total = len(self._journal.entries)
        self._count_label.set_text(f"{total} total entries")

    def refresh(self):
        """Public method to refresh the journal view."""
        self._refresh()
