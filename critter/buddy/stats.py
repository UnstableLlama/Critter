"""
Tamagotchi-style stats for the critter companion.
Hunger, happiness, energy, bonding - the classic four.
Persists to ~/.config/critter/state.json between sessions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("critter.stats")

STATE_PATH = Path.home() / ".config" / "critter" / "state.json"

# Decay rates per hour
HUNGER_DECAY = 5.0
HAPPINESS_DECAY = 2.0
ENERGY_DECAY_ACTIVE = 8.0
ENERGY_RECOVERY_IDLE = 3.0

# Button effects
FEED_AMOUNT = 25.0
PLAY_AMOUNT = 20.0
REST_AMOUNT = 25.0
PET_AMOUNT = 3.0

# Event bonuses
EVENT_BONDING = 0.1
SUCCESS_HAPPINESS = 5.0
ERROR_HAPPINESS = -3.0
MILESTONE_BONDING = 1.0


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


@dataclass
class CritterStats:
    """The critter's vital statistics. Decays over time, boosted by care."""

    hunger: float = 80.0
    happiness: float = 75.0
    energy: float = 90.0
    bonding: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)
    total_sessions: int = 0
    total_tool_calls: int = 0
    total_active_minutes: float = 0
    longest_streak_minutes: float = 0
    days_active: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_day_seen: str = ""
    _current_streak_start: datetime | None = field(default=None, repr=False)
    milestones: list[str] = field(default_factory=list)

    def decay(self, is_active: bool = False):
        """Apply time-based stat changes since last update."""
        now = datetime.now()
        elapsed_hours = (now - self.last_update).total_seconds() / 3600.0

        if elapsed_hours < 0.001:
            return

        # Cap decay at 24 hours to prevent stats from zeroing after long absence
        elapsed_hours = min(elapsed_hours, 24.0)

        self.hunger = _clamp(self.hunger - HUNGER_DECAY * elapsed_hours)
        self.happiness = _clamp(self.happiness - HAPPINESS_DECAY * elapsed_hours)

        if is_active:
            self.energy = _clamp(self.energy - ENERGY_DECAY_ACTIVE * elapsed_hours)
            self.total_active_minutes += elapsed_hours * 60

            if self._current_streak_start:
                streak = (now - self._current_streak_start).total_seconds() / 60.0
                self.longest_streak_minutes = max(
                    self.longest_streak_minutes, streak
                )
        else:
            self.energy = _clamp(self.energy + ENERGY_RECOVERY_IDLE * elapsed_hours)
            self._current_streak_start = None

        # Track unique days
        today = now.strftime("%Y-%m-%d")
        if today != self.last_day_seen:
            self.days_active += 1
            self.last_day_seen = today

        self.last_update = now

    # ---- The 4 tamagotchi buttons ----

    def feed(self) -> str:
        """Feed the critter. Returns a reaction string."""
        self.hunger = _clamp(self.hunger + FEED_AMOUNT)
        self.bonding = _clamp(self.bonding + 0.5)
        return "Yum!"

    def play(self) -> str:
        """Play with the critter."""
        self.happiness = _clamp(self.happiness + PLAY_AMOUNT)
        self.energy = _clamp(self.energy - 5)
        self.bonding = _clamp(self.bonding + 0.5)
        return "Wheee!"

    def rest(self) -> str:
        """Let the critter rest."""
        self.energy = _clamp(self.energy + REST_AMOUNT)
        return "Ahhh..."

    def pet(self) -> str:
        """Pet the critter. Maximum bonding boost."""
        self.bonding = _clamp(self.bonding + PET_AMOUNT)
        self.happiness = _clamp(self.happiness + 5)
        return "<3"

    # ---- Event reactions ----

    def on_session_start(self):
        self.total_sessions += 1
        self.bonding = _clamp(self.bonding + EVENT_BONDING)
        self._current_streak_start = datetime.now()

    def on_tool_call(self):
        self.total_tool_calls += 1
        self.bonding = _clamp(self.bonding + EVENT_BONDING * 0.5)

    def on_success(self):
        self.happiness = _clamp(self.happiness + SUCCESS_HAPPINESS)
        self.bonding = _clamp(self.bonding + EVENT_BONDING)

    def on_error(self):
        self.happiness = _clamp(self.happiness + ERROR_HAPPINESS)

    def on_milestone(self):
        self.bonding = _clamp(self.bonding + MILESTONE_BONDING)

    # ---- Stat status helpers ----

    @property
    def needs_feeding(self) -> bool:
        return self.hunger < 30

    @property
    def needs_rest(self) -> bool:
        return self.energy < 30

    @property
    def needs_play(self) -> bool:
        return self.happiness < 30

    @property
    def is_critical(self) -> bool:
        return self.hunger < 15 or self.energy < 15 or self.happiness < 15

    # ---- Persistence ----

    def save(self):
        """Save stats to disk."""
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "hunger": round(self.hunger, 1),
            "happiness": round(self.happiness, 1),
            "energy": round(self.energy, 1),
            "bonding": round(self.bonding, 2),
            "last_update": self.last_update.isoformat(),
            "total_sessions": self.total_sessions,
            "total_tool_calls": self.total_tool_calls,
            "total_active_minutes": round(self.total_active_minutes, 1),
            "longest_streak_minutes": round(self.longest_streak_minutes, 1),
            "days_active": self.days_active,
            "first_seen": self.first_seen.isoformat(),
            "last_day_seen": self.last_day_seen,
            "milestones": self.milestones,
        }
        STATE_PATH.write_text(json.dumps(data, indent=2))

    @staticmethod
    def load() -> CritterStats:
        """Load stats from disk, applying offline decay."""
        if not STATE_PATH.exists():
            stats = CritterStats()
            stats.save()
            return stats

        try:
            data = json.loads(STATE_PATH.read_text())
            stats = CritterStats(
                hunger=data.get("hunger", 80.0),
                happiness=data.get("happiness", 75.0),
                energy=data.get("energy", 90.0),
                bonding=data.get("bonding", 0.0),
                last_update=(
                    datetime.fromisoformat(data["last_update"])
                    if "last_update" in data
                    else datetime.now()
                ),
                total_sessions=data.get("total_sessions", 0),
                total_tool_calls=data.get("total_tool_calls", 0),
                total_active_minutes=data.get("total_active_minutes", 0),
                longest_streak_minutes=data.get("longest_streak_minutes", 0),
                days_active=data.get("days_active", 0),
                first_seen=(
                    datetime.fromisoformat(data["first_seen"])
                    if "first_seen" in data
                    else datetime.now()
                ),
                last_day_seen=data.get("last_day_seen", ""),
                milestones=data.get("milestones", []),
            )
            # Apply decay for time spent offline
            stats.decay(is_active=False)
            return stats
        except Exception:
            logger.exception("Failed to load stats, starting fresh")
            return CritterStats()

    def bar(self, stat_name: str, width: int = 10) -> str:
        """Render a text-based stat bar: [========  ] 80"""
        val = getattr(self, stat_name, 0)
        filled = round(val / 100 * width)
        empty = width - filled
        return f"[{'=' * filled}{' ' * empty}] {int(val):>3}"
