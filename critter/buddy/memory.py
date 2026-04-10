"""
Critter memory - the critter remembers things about its human.
Tracks favorite projects, most-used tools, coding patterns,
and generates personalized observations.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("critter.memory")

MEMORY_PATH = Path.home() / ".config" / "critter" / "memory.json"


@dataclass
class CritterMemory:
    """The critter's long-term memory of its human's habits."""

    project_visits: Counter = field(default_factory=Counter)
    tool_usage: Counter = field(default_factory=Counter)
    hour_activity: Counter = field(default_factory=Counter)
    error_count: int = 0
    approval_count: int = 0
    denial_count: int = 0

    def remember_project(self, project_name: str):
        """Record a visit to a project."""
        self.project_visits[project_name] += 1

    def remember_tool(self, tool_name: str):
        """Record a tool being used."""
        self.tool_usage[tool_name] += 1

    def remember_activity(self):
        """Record activity at the current hour."""
        hour = datetime.now().hour
        self.hour_activity[str(hour)] += 1

    def remember_error(self):
        self.error_count += 1

    def remember_approval(self):
        self.approval_count += 1

    def remember_denial(self):
        self.denial_count += 1

    # ---- Insights ----

    @property
    def favorite_project(self) -> str | None:
        """The project visited most often."""
        if not self.project_visits:
            return None
        return self.project_visits.most_common(1)[0][0]

    @property
    def favorite_tools(self) -> list[str]:
        """Top 3 most-used tools."""
        return [t for t, _ in self.tool_usage.most_common(3)]

    @property
    def peak_hours(self) -> list[int]:
        """Top 3 most active hours of the day."""
        if not self.hour_activity:
            return []
        return [int(h) for h, _ in self.hour_activity.most_common(3)]

    @property
    def is_night_owl(self) -> bool:
        """Does the human code more at night?"""
        night_count = sum(
            self.hour_activity.get(str(h), 0) for h in range(22, 24)
        ) + sum(self.hour_activity.get(str(h), 0) for h in range(0, 6))
        day_count = sum(
            self.hour_activity.get(str(h), 0) for h in range(6, 22)
        )
        return night_count > day_count * 0.5 if day_count else False

    @property
    def is_early_bird(self) -> bool:
        """Does the human code more in the morning?"""
        morning = sum(
            self.hour_activity.get(str(h), 0) for h in range(5, 10)
        )
        total = sum(self.hour_activity.values())
        return morning > total * 0.3 if total else False

    @property
    def trust_ratio(self) -> float:
        """How often does the human approve vs deny?"""
        total = self.approval_count + self.denial_count
        if total == 0:
            return 1.0
        return self.approval_count / total

    def generate_observation(self) -> str | None:
        """Generate a personalized observation about the human's habits.
        Returns None if there's not enough data yet.
        """
        observations = []

        if self.favorite_project:
            count = self.project_visits[self.favorite_project]
            if count >= 5:
                observations.append(
                    f"My human really loves working on {self.favorite_project}. "
                    f"We've been there {count} times!"
                )

        if self.is_night_owl:
            observations.append(
                "My human is a night owl! We do our best work "
                "when the world is sleeping."
            )
        elif self.is_early_bird:
            observations.append(
                "My human is an early bird! Fresh code before breakfast."
            )

        if len(self.favorite_tools) >= 3:
            tools = ", ".join(self.favorite_tools[:3])
            observations.append(
                f"My human's favorite tools are {tools}. "
                "I know them well by now!"
            )

        if self.trust_ratio > 0.9 and self.approval_count > 10:
            observations.append(
                "My human almost always approves what I show them. "
                "We really trust each other!"
            )

        if self.error_count > 50:
            observations.append(
                f"We've seen {self.error_count} errors together. "
                "But we always figure it out!"
            )

        if not observations:
            return None

        import random

        return random.choice(observations)

    # ---- Persistence ----

    def save(self):
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "project_visits": dict(self.project_visits),
            "tool_usage": dict(self.tool_usage),
            "hour_activity": dict(self.hour_activity),
            "error_count": self.error_count,
            "approval_count": self.approval_count,
            "denial_count": self.denial_count,
        }
        MEMORY_PATH.write_text(json.dumps(data, indent=2))

    @staticmethod
    def load() -> CritterMemory:
        if not MEMORY_PATH.exists():
            return CritterMemory()
        try:
            data = json.loads(MEMORY_PATH.read_text())
            mem = CritterMemory(
                project_visits=Counter(data.get("project_visits", {})),
                tool_usage=Counter(data.get("tool_usage", {})),
                hour_activity=Counter(data.get("hour_activity", {})),
                error_count=data.get("error_count", 0),
                approval_count=data.get("approval_count", 0),
                denial_count=data.get("denial_count", 0),
            )
            return mem
        except Exception:
            logger.exception("Failed to load memory")
            return CritterMemory()
