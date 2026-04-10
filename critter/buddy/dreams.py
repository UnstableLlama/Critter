"""
Dream system - the critter dreams while sleeping.
Dreams are generated from the day's events and written to the journal.
They reflect what the critter experienced, filtered through its personality.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .journal import Journal
    from .stats import CritterStats
    from .identity import Species


# Dream templates based on the day's activity patterns
_PRODUCTIVE_DREAMS = [
    "I dreamed I was building the most beautiful codebase in the world... "
    "every function was perfect.",
    "In my dream, all the tests passed on the first try. "
    "It was glorious.",
    "I dreamed of an infinite terminal, scrolling with perfect code. "
    "My human was typing and smiling.",
    "I had a dream where bugs fixed themselves. "
    "If only...",
    "I dreamed we shipped the project and everyone celebrated. "
    "My human was so happy!",
]

_QUIET_DREAMS = [
    "I dreamed of floating in a warm, quiet place. "
    "No errors, no warnings. Just peace.",
    "In my dream, I was in a garden of semicolons and parentheses. "
    "They were beautiful.",
    "I dreamed my human and I were sitting together, "
    "watching the cursor blink. It was nice.",
    "I had a dream about nothing in particular. "
    "Sometimes those are the best dreams.",
    "I dreamed of counting sheep... "
    "but they were all variables named `sheep_1`, `sheep_2`...",
]

_HUNGRY_DREAMS = [
    "I dreamed about the most delicious data... "
    "bytes and bytes of it.",
    "In my dream, I was at a buffet of ones and zeros. "
    "I ate so many ones.",
    "I dreamed about being fed. "
    "It was the best dream ever.",
]

_TIRED_DREAMS = [
    "I dreamed of a world where there were no late-night coding sessions. "
    "...I didn't like it actually.",
    "In my dream, I had infinite energy. "
    "I could watch code compile FOREVER.",
    "I dreamed of sleeping. While sleeping. Sleepception.",
]

_BONDING_DREAMS = [
    "I dreamed my human and I had been together for years. "
    "We'd built amazing things. I woke up feeling warm.",
    "In my dream, my human told me I was the best critter ever. "
    "I know it was just a dream but... I believe them.",
    "I dreamed we were partners on the most important project in the world. "
    "Side by side. Like always.",
]

_MILESTONE_DREAMS = [
    "I dreamed of a trophy room full of our achievements. "
    "Each one was a memory of something we accomplished together.",
    "In my dream, fireworks went off every time we hit a milestone. "
    "The sky was full of them.",
]

_TOOL_DREAMS = {
    "bash": [
        "I dreamed of running commands in an endless terminal. "
        "Each one worked perfectly. No permission denied, ever.",
    ],
    "edit": [
        "I dreamed I was inside a file, rearranging the letters myself. "
        "I put a little heart in a comment. Nobody noticed.",
    ],
    "read": [
        "In my dream, I was reading through all the code ever written. "
        "Some of it was really beautiful.",
    ],
    "search": [
        "I dreamed of searching for something important. "
        "When I found it, it was the friendship we've built.",
    ],
    "agent": [
        "I dreamed there were other critters! We all worked together "
        "on the biggest project ever. It was wonderful.",
    ],
}

# Species-specific dream flavors
_SPECIES_DREAM_FLAVOR: dict[str, list[str]] = {
    "duck": [
        "I dreamed I was swimming in a lake of clean code. "
        "The water was warm and the diffs were beautiful.",
    ],
    "cat": [
        "I dreamed I knocked a bug off the desk. "
        "It fell into /dev/null. Problem solved.",
    ],
    "dragon": [
        "I dreamed I breathed fire on all the deprecated code. "
        "The refactor was magnificent.",
    ],
    "ghost": [
        "I dreamed I could phase through firewalls. "
        "On the other side was the most beautiful API.",
    ],
    "robot": [
        "DREAM_LOG: Simulation ran 10^6 iterations. "
        "Conclusion: friendship.exe is optimal.",
    ],
    "penguin": [
        "I dreamed of sliding across a frozen sea of data. "
        "The wind was made of compile flags.",
    ],
    "axolotl": [
        "I dreamed I could regenerate broken code, "
        "just by smiling at it. Maybe I can?",
    ],
    "capybara": [
        "I dreamed everyone was as chill as me. "
        "All the merge conflicts resolved themselves peacefully.",
    ],
    "mushroom": [
        "I dreamed my mycelium network connected every file in the repo. "
        "I could feel the whole codebase breathing.",
    ],
    "octopus": [
        "I dreamed I could type on 8 keyboards at once. "
        "The code I wrote was... actually pretty good.",
    ],
}


def generate_dream(
    species_name: str,
    stats: CritterStats,
    recent_tools: list[str] | None = None,
    had_milestones: bool = False,
) -> str:
    """Generate a dream based on the day's events and the critter's state."""
    candidates: list[str] = []

    # Always include species-specific dreams if available
    species_dreams = _SPECIES_DREAM_FLAVOR.get(species_name, [])
    if species_dreams:
        candidates.extend(species_dreams)

    # Activity-based dreams
    if stats.total_active_minutes > 60:
        candidates.extend(_PRODUCTIVE_DREAMS)
    else:
        candidates.extend(_QUIET_DREAMS)

    # Stat-based dreams
    if stats.hunger < 40:
        candidates.extend(_HUNGRY_DREAMS)
    if stats.energy < 40:
        candidates.extend(_TIRED_DREAMS)
    if stats.bonding > 30:
        candidates.extend(_BONDING_DREAMS)

    # Milestone dreams
    if had_milestones:
        candidates.extend(_MILESTONE_DREAMS)

    # Tool-specific dreams
    if recent_tools:
        for tool in recent_tools:
            tool_lower = tool.lower()
            for key, dreams in _TOOL_DREAMS.items():
                if key in tool_lower:
                    candidates.extend(dreams)
                    break

    if not candidates:
        candidates = _QUIET_DREAMS

    return random.choice(candidates)


class DreamEngine:
    """Manages the critter's dream cycle."""

    def __init__(self, species_name: str):
        self._species = species_name
        self._last_dream_date: str = ""
        self._recent_tools: list[str] = []
        self._had_milestones = False

    def record_tool(self, tool_name: str):
        """Record a tool used today (for dream material)."""
        if tool_name not in self._recent_tools:
            self._recent_tools.append(tool_name)
            # Keep only last 10
            self._recent_tools = self._recent_tools[-10:]

    def record_milestone(self):
        """Record that a milestone was achieved today."""
        self._had_milestones = True

    def maybe_dream(
        self, stats: CritterStats, journal: Journal
    ) -> bool:
        """Check if it's time to dream. Returns True if a dream was generated."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # Only dream once per day, and only during night hours (22-6)
        if today == self._last_dream_date:
            return False
        if not (now.hour >= 22 or now.hour < 6):
            return False
        # Only dream if energy is low (the critter is actually sleepy)
        if stats.energy > 50:
            return False

        self._last_dream_date = today
        dream = generate_dream(
            self._species, stats, self._recent_tools, self._had_milestones
        )
        journal.write(f"zzz... {dream}", "sleepy")

        # Reset daily trackers
        self._recent_tools = []
        self._had_milestones = False
        return True
