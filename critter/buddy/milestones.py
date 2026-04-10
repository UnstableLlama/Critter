"""
Achievement/milestone tracking for the critter companion.
Milestones celebrate the journey of coding together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .stats import CritterStats


@dataclass
class Milestone:
    id: str
    name: str
    description: str
    check: Callable  # (CritterStats) -> bool


# All achievable milestones, ordered roughly by difficulty
MILESTONES: list[Milestone] = [
    # Session milestones
    Milestone(
        "first_session", "First Steps",
        "Complete your first coding session",
        lambda s: s.total_sessions >= 1,
    ),
    Milestone(
        "sessions_10", "Getting Started",
        "Complete 10 coding sessions",
        lambda s: s.total_sessions >= 10,
    ),
    Milestone(
        "sessions_50", "Regular",
        "Complete 50 coding sessions",
        lambda s: s.total_sessions >= 50,
    ),
    Milestone(
        "sessions_100", "Veteran",
        "Complete 100 coding sessions",
        lambda s: s.total_sessions >= 100,
    ),
    Milestone(
        "sessions_500", "Legend",
        "Complete 500 coding sessions",
        lambda s: s.total_sessions >= 500,
    ),

    # Tool call milestones
    Milestone(
        "tools_10", "Tool User",
        "Witness 10 tool calls",
        lambda s: s.total_tool_calls >= 10,
    ),
    Milestone(
        "tools_100", "Tool Master",
        "Witness 100 tool calls",
        lambda s: s.total_tool_calls >= 100,
    ),
    Milestone(
        "tools_500", "Tool Legend",
        "Witness 500 tool calls",
        lambda s: s.total_tool_calls >= 500,
    ),
    Milestone(
        "tools_1000", "Tool Mythic",
        "Witness 1,000 tool calls",
        lambda s: s.total_tool_calls >= 1000,
    ),
    Milestone(
        "tools_5000", "Tool Transcendent",
        "Witness 5,000 tool calls",
        lambda s: s.total_tool_calls >= 5000,
    ),

    # Time milestones
    Milestone(
        "hour_1", "Hour One",
        "Code for 1 hour total",
        lambda s: s.total_active_minutes >= 60,
    ),
    Milestone(
        "hour_10", "Dedicated",
        "Code for 10 hours total",
        lambda s: s.total_active_minutes >= 600,
    ),
    Milestone(
        "hour_50", "Committed",
        "Code for 50 hours total",
        lambda s: s.total_active_minutes >= 3000,
    ),
    Milestone(
        "hour_100", "Centurion",
        "Code for 100 hours total",
        lambda s: s.total_active_minutes >= 6000,
    ),

    # Streak milestones
    Milestone(
        "streak_30", "Focus Mode",
        "Code for 30 minutes straight",
        lambda s: s.longest_streak_minutes >= 30,
    ),
    Milestone(
        "streak_60", "In The Zone",
        "Code for 1 hour straight",
        lambda s: s.longest_streak_minutes >= 60,
    ),
    Milestone(
        "streak_120", "Flow State",
        "Code for 2 hours straight",
        lambda s: s.longest_streak_minutes >= 120,
    ),
    Milestone(
        "streak_240", "Marathon",
        "Code for 4 hours straight",
        lambda s: s.longest_streak_minutes >= 240,
    ),

    # Bonding milestones
    Milestone(
        "bond_10", "Acquaintance",
        "Reach bonding level 10",
        lambda s: s.bonding >= 10,
    ),
    Milestone(
        "bond_25", "Friend",
        "Reach bonding level 25",
        lambda s: s.bonding >= 25,
    ),
    Milestone(
        "bond_50", "Best Friend",
        "Reach bonding level 50",
        lambda s: s.bonding >= 50,
    ),
    Milestone(
        "bond_75", "Soulmate",
        "Reach bonding level 75",
        lambda s: s.bonding >= 75,
    ),
    Milestone(
        "bond_100", "Inseparable",
        "Reach maximum bonding",
        lambda s: s.bonding >= 100,
    ),

    # Day milestones
    Milestone(
        "days_7", "One Week",
        "Use Critter for 7 days",
        lambda s: s.days_active >= 7,
    ),
    Milestone(
        "days_30", "One Month",
        "Use Critter for 30 days",
        lambda s: s.days_active >= 30,
    ),
    Milestone(
        "days_100", "Centenarian",
        "Use Critter for 100 days",
        lambda s: s.days_active >= 100,
    ),
    Milestone(
        "days_365", "Anniversary",
        "Use Critter for a full year",
        lambda s: s.days_active >= 365,
    ),
]


def check_milestones(stats: CritterStats) -> list[Milestone]:
    """Check for newly achieved milestones. Returns list of new ones."""
    newly_achieved = []
    for m in MILESTONES:
        if m.id not in stats.milestones and m.check(stats):
            newly_achieved.append(m)
            stats.milestones.append(m.id)
    return newly_achieved
