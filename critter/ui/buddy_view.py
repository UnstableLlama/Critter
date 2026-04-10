"""
Buddy ASCII art display widget with tamagotchi stats and care buttons.
Shows the animated buddy sprite, mood, vital stats, and 4 care buttons.
"""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, GLib

from ..buddy.animator import SpriteAnimator
from ..buddy.growth import GrowthStage
from ..buddy.identity import BuddyIdentity, Task
from ..buddy.mood import Mood
from ..buddy.stats import CritterStats


def _stat_bar(label: str, value: float, width: int = 10) -> str:
    """Render a compact text stat bar: LBL [========  ] 80"""
    filled = round(value / 100 * width)
    empty = width - filled
    bar = "=" * filled + " " * empty
    return f"{label} [{bar}] {int(value):>3}"


class BuddyView(Gtk.Box):
    """Displays the buddy sprite, mood, stats, and 4 care buttons."""

    def __init__(
        self,
        identity: BuddyIdentity,
        on_feed: Callable[[], None] | None = None,
        on_play: Callable[[], None] | None = None,
        on_rest: Callable[[], None] | None = None,
        on_pet: Callable[[], None] | None = None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        self._on_feed = on_feed
        self._on_play = on_play
        self._on_rest = on_rest
        self._on_pet = on_pet
        self._reaction_timeout_id: int | None = None

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

        # Mood label
        self._mood_label = Gtk.Label(label="Content")
        self._mood_label.get_style_context().add_class("buddy-status")
        font_desc_sm = Pango.FontDescription.from_string("monospace 10")
        attr_small = Pango.AttrList.new()
        attr_small.insert(Pango.attr_font_desc_new(font_desc_sm))
        self._mood_label.set_attributes(attr_small)
        self.append(self._mood_label)

        # Stats display (monospace text bars)
        self._stats_label = Gtk.Label()
        self._stats_label.set_wrap(False)
        font_stats = Pango.FontDescription.from_string("monospace 8")
        stats_attr = Pango.AttrList.new()
        stats_attr.insert(Pango.attr_font_desc_new(font_stats))
        self._stats_label.set_attributes(stats_attr)
        self._stats_label.set_margin_top(6)
        self._stats_label.get_style_context().add_class("stats-display")
        self.append(self._stats_label)

        # Reaction label (briefly shows button feedback)
        self._reaction_label = Gtk.Label(label="")
        self._reaction_label.get_style_context().add_class("reaction-label")
        reaction_attr = Pango.AttrList.new()
        reaction_attr.insert(
            Pango.attr_font_desc_new(
                Pango.FontDescription.from_string("monospace 11")
            )
        )
        self._reaction_label.set_attributes(reaction_attr)
        self._reaction_label.set_margin_top(2)
        self.append(self._reaction_label)

        # 4 tamagotchi buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(6)
        btn_box.set_margin_bottom(4)

        self._feed_btn = self._make_button("Feed", self._on_feed_clicked)
        self._play_btn = self._make_button("Play", self._on_play_clicked)
        self._rest_btn = self._make_button("Rest", self._on_rest_clicked)
        self._pet_btn = self._make_button("Pet", self._on_pet_clicked)

        btn_box.append(self._feed_btn)
        btn_box.append(self._play_btn)
        btn_box.append(self._rest_btn)
        btn_box.append(self._pet_btn)
        self.append(btn_box)

        # Set callback and render initial frame
        self._animator.set_callback(self._on_frame)
        self._render_body()

    def _make_button(self, label: str, callback) -> Gtk.Button:
        btn = Gtk.Button(label=label)
        btn.set_size_request(60, -1)
        btn.get_style_context().add_class("tamagotchi-btn")
        btn.connect("clicked", callback)
        return btn

    def start(self):
        """Start animation timer (call after widget is realized)."""
        self._animator.start()

    def stop(self):
        self._animator.stop()

    def set_task(self, task: Task):
        self._animator.task = task
        self._render_body()

    def set_mood(self, mood: Mood):
        """Update the mood display and pass to animator."""
        self._animator.mood = mood
        self._mood_label.set_text(mood.display)
        self._render_body()

    def update_stats(self, stats: CritterStats):
        """Update the stat bars display."""
        lines = [
            _stat_bar("HGR", stats.hunger) + "  " + _stat_bar("HPY", stats.happiness),
            _stat_bar("NRG", stats.energy) + "  " + _stat_bar("BND", stats.bonding),
        ]
        self._stats_label.set_text("\n".join(lines))

        # Highlight buttons that would help
        self._feed_btn.get_style_context().remove_class("needs-attention")
        self._rest_btn.get_style_context().remove_class("needs-attention")
        self._play_btn.get_style_context().remove_class("needs-attention")
        if stats.needs_feeding:
            self._feed_btn.get_style_context().add_class("needs-attention")
        if stats.needs_rest:
            self._rest_btn.get_style_context().add_class("needs-attention")
        if stats.needs_play:
            self._play_btn.get_style_context().add_class("needs-attention")

    def show_reaction(self, text: str):
        """Show a brief reaction text that fades after a moment."""
        self._reaction_label.set_text(text)
        if self._reaction_timeout_id:
            GLib.source_remove(self._reaction_timeout_id)
        self._reaction_timeout_id = GLib.timeout_add(
            2000, self._clear_reaction
        )

    def _clear_reaction(self) -> bool:
        self._reaction_label.set_text("")
        self._reaction_timeout_id = None
        return False

    # ---- Button handlers ----

    def _on_feed_clicked(self, _btn):
        if self._on_feed:
            self._on_feed()

    def _on_play_clicked(self, _btn):
        if self._on_play:
            self._on_play()

    def _on_rest_clicked(self, _btn):
        if self._on_rest:
            self._on_rest()

    def _on_pet_clicked(self, _btn):
        if self._on_pet:
            self._on_pet()

    # ---- Rendering ----

    def _on_frame(self, frame_string: str, one_line: str):
        self._render_body()

    def _render_body(self):
        lines = self._animator.render_body()
        self._sprite_label.set_text("\n".join(lines))

    def set_growth_stage(self, stage: GrowthStage):
        """Update the displayed growth stage."""
        name = self._identity_ref.name or self._identity_ref.species.value.title()
        prefix = stage.title_prefix
        self._name_label.set_markup(
            f"<b>{prefix}{name}</b>  "
            f"<small>({self._identity_ref.species.value} - {stage.display_name})</small>"
        )

    def _format_name(self, identity: BuddyIdentity) -> str:
        self._identity_ref = identity
        name = identity.name or identity.species.value.title()
        return f"<b>{name}</b>  <small>({identity.species.value})</small>"
