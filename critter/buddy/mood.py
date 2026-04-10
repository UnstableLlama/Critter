"""
Mood and emotion system for the critter companion.
Mood is derived from stats, time of day, and recent activity.
Affects face expression, idle behaviors, and journal tone.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum


class Mood(str, Enum):
    HAPPY = "happy"
    CONTENT = "content"
    CURIOUS = "curious"
    WORRIED = "worried"
    TIRED = "tired"
    EXCITED = "excited"
    SLEEPY = "sleepy"
    PROUD = "proud"
    NERVOUS = "nervous"
    BORED = "bored"
    LOVE = "love"

    @property
    def eye_override(self) -> str | None:
        """Override eye character for this mood, or None to use default."""
        return {
            Mood.HAPPY: "^",
            Mood.CONTENT: None,
            Mood.CURIOUS: None,
            Mood.WORRIED: ";",
            Mood.TIRED: "-",
            Mood.EXCITED: "*",
            Mood.SLEEPY: "-",
            Mood.PROUD: "^",
            Mood.NERVOUS: ";",
            Mood.BORED: ".",
            Mood.LOVE: "*",
        }.get(self)

    @property
    def face_suffix(self) -> str:
        """Extra characters appended to the face for this mood."""
        return {
            Mood.HAPPY: "",
            Mood.CONTENT: "",
            Mood.CURIOUS: "?",
            Mood.WORRIED: "",
            Mood.TIRED: "",
            Mood.EXCITED: "!",
            Mood.SLEEPY: " zzz",
            Mood.PROUD: "!",
            Mood.NERVOUS: "",
            Mood.BORED: "...",
            Mood.LOVE: " <3",
        }.get(self, "")

    @property
    def display(self) -> str:
        """Human-readable mood name."""
        return {
            Mood.HAPPY: "Happy",
            Mood.CONTENT: "Content",
            Mood.CURIOUS: "Curious",
            Mood.WORRIED: "Worried",
            Mood.TIRED: "Tired",
            Mood.EXCITED: "Excited!",
            Mood.SLEEPY: "Sleepy",
            Mood.PROUD: "Proud!",
            Mood.NERVOUS: "Nervous",
            Mood.BORED: "Bored",
            Mood.LOVE: "Feeling loved",
        }.get(self, self.value.title())


class TimeOfDay(str, Enum):
    MORNING = "morning"      # 6-12
    AFTERNOON = "afternoon"  # 12-18
    EVENING = "evening"      # 18-22
    NIGHT = "night"          # 22-6

    @staticmethod
    def current() -> TimeOfDay:
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return TimeOfDay.MORNING
        if 12 <= hour < 18:
            return TimeOfDay.AFTERNOON
        if 18 <= hour < 22:
            return TimeOfDay.EVENING
        return TimeOfDay.NIGHT

    @property
    def greeting(self) -> str:
        return {
            TimeOfDay.MORNING: "Good morning",
            TimeOfDay.AFTERNOON: "Good afternoon",
            TimeOfDay.EVENING: "Good evening",
            TimeOfDay.NIGHT: "It's late",
        }[self]


class MoodEngine:
    """Derives the critter's current mood from stats and context."""

    def __init__(self):
        self._mood = Mood.CONTENT
        self._override: Mood | None = None
        self._override_ticks = 0

    @property
    def mood(self) -> Mood:
        if self._override and self._override_ticks > 0:
            return self._override
        return self._mood

    def set_temporary_mood(self, mood: Mood, ticks: int = 10):
        """Set a temporary mood override (e.g. after being petted)."""
        self._override = mood
        self._override_ticks = ticks

    def tick(self):
        """Advance the override countdown by one tick."""
        if self._override_ticks > 0:
            self._override_ticks -= 1

    def derive(
        self,
        hunger: float,
        happiness: float,
        energy: float,
        bonding: float,
        is_active: bool,
    ) -> Mood:
        """Derive mood from current stats, time of day, and activity state."""
        tod = TimeOfDay.current()

        # Critical stat warnings (highest priority)
        if hunger < 15:
            self._mood = Mood.WORRIED
            return self._mood
        if energy < 15:
            self._mood = (
                Mood.SLEEPY
                if tod in (TimeOfDay.NIGHT, TimeOfDay.EVENING)
                else Mood.TIRED
            )
            return self._mood

        # Activity-driven moods
        if is_active:
            self._mood = Mood.EXCITED if happiness > 70 else Mood.CURIOUS
            return self._mood

        # Night + low energy
        if tod == TimeOfDay.NIGHT and energy < 40:
            self._mood = Mood.SLEEPY
            return self._mood

        # Happiness-driven
        if happiness > 80 and hunger > 60:
            self._mood = Mood.HAPPY
            return self._mood
        if happiness < 30:
            self._mood = Mood.BORED
            return self._mood
        if happiness < 50 and energy < 40:
            self._mood = Mood.TIRED
            return self._mood

        self._mood = Mood.CONTENT
        return self._mood
