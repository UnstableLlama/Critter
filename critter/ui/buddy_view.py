"""
Buddy ASCII art display widget.
Shows the animated buddy sprite in a monospace label.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

from ..buddy.animator import SpriteAnimator
from ..buddy.identity import BuddyIdentity, Task


class BuddyView(Gtk.Box):
    """Displays the buddy ASCII sprite with animation."""

    def __init__(self, identity: BuddyIdentity):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        self._animator = SpriteAnimator(identity)

        # Sprite display (multi-line monospace)
        self._sprite_label = Gtk.Label()
        self._sprite_label.set_wrap(False)
        self._sprite_label.set_selectable(False)
        font_desc = Pango.FontDescription.from_string("monospace 14")
        self._sprite_label.get_style_context().add_class("buddy-sprite")
        attr_list = Pango.AttrList.new()
        attr_list.insert(Pango.attr_font_desc_new(font_desc))
        self._sprite_label.set_attributes(attr_list)
        self.append(self._sprite_label)

        # Name / species label
        self._name_label = Gtk.Label()
        self._name_label.get_style_context().add_class("buddy-name")
        self._name_label.set_markup(self._format_name(identity))
        self.append(self._name_label)

        # Rarity stars
        self._rarity_label = Gtk.Label(label=identity.rarity.stars)
        self._rarity_label.get_style_context().add_class("buddy-rarity")
        self.append(self._rarity_label)

        # Status label (one-line face + task)
        self._status_label = Gtk.Label()
        self._status_label.get_style_context().add_class("buddy-status")
        font_desc_sm = Pango.FontDescription.from_string("monospace 10")
        attr_small = Pango.AttrList.new()
        attr_small.insert(Pango.attr_font_desc_new(font_desc_sm))
        self._status_label.set_attributes(attr_small)
        self.append(self._status_label)

        # Set callback and start animation
        self._animator.set_callback(self._on_frame)
        self._render_body()

    def start(self):
        """Start animation timer (call after widget is realized)."""
        self._animator.start()

    def stop(self):
        self._animator.stop()

    def set_task(self, task: Task):
        self._animator.task = task
        self._render_body()

    def _on_frame(self, frame_string: str, one_line: str):
        self._status_label.set_text(one_line)
        self._render_body()

    def _render_body(self):
        lines = self._animator.render_body()
        self._sprite_label.set_text("\n".join(lines))

    def _format_name(self, identity: BuddyIdentity) -> str:
        name = identity.name or identity.species.value.title()
        return f"<b>{name}</b>  <small>({identity.species.value})</small>"
