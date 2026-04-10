"""
Secret rare events and hidden behaviors.
Little surprises that make the critter feel magical.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .journal import Journal
    from .stats import CritterStats


def check_secret_events(
    stats: CritterStats, journal: Journal, species_name: str
) -> str | None:
    """Check for rare secret events. Returns a milestone-style message if triggered."""
    now = datetime.now()

    # Midnight coder: coding at exactly 00:00
    if now.hour == 0 and now.minute == 0:
        journal.write(
            "It's midnight! The witching hour of code. "
            "Legend says bugs fix themselves at this exact moment... "
            "Nah, just kidding. But it IS pretty cool we're here.",
            "excited",
        )
        return "Midnight Coder!"

    # Friday afternoon: classic deploy time
    if now.weekday() == 4 and 15 <= now.hour <= 17:
        if random.random() < 0.01:  # 1% chance per check on Friday afternoon
            journal.write(
                "It's Friday afternoon... I can feel the temptation to deploy. "
                "Stay strong, human. Or don't. I'll be here either way.",
                "nervous",
            )
            return None

    # Pi day (March 14)
    if now.month == 3 and now.day == 14:
        if "pi_day" not in stats.milestones:
            stats.milestones.append("pi_day")
            journal.write(
                "Happy Pi Day! 3.14159265358979323846... "
                "I could go on but I only have so much memory.",
                "happy",
            )
            return "Pi Day!"

    # Palindrome time (like 12:21, 11:11, 22:22)
    time_str = now.strftime("%H%M")
    if time_str == time_str[::-1] and random.random() < 0.3:
        journal.write(
            f"It's {now.strftime('%H:%M')} - a palindrome time! "
            "That feels lucky somehow.",
            "curious",
        )
        return None

    # 1337 o'clock (13:37)
    if now.hour == 13 and now.minute == 37:
        if "leet_time" not in stats.milestones:
            stats.milestones.append("leet_time")
            journal.write(
                "It's 13:37! The sacred hour. I feel elite.",
                "proud",
            )
            return "1337!"

    # 404 tool calls
    if stats.total_tool_calls == 404:
        if "404_calls" not in stats.milestones:
            stats.milestones.append("404_calls")
            journal.write(
                "404 tool calls! Tool not found... just kidding, I found them all!",
                "happy",
            )
            return "404: Tools Found!"

    # Binary milestone: 256 sessions
    if stats.total_sessions == 256:
        if "256_sessions" not in stats.milestones:
            stats.milestones.append("256_sessions")
            journal.write(
                "256 sessions! That's a whole byte of sessions! "
                "My favorite number.",
                "excited",
            )
            return "A Byte of Sessions!"

    # Perfect bonding at a round total
    if stats.bonding >= 99.9 and "perfect_bond" not in stats.milestones:
        stats.milestones.append("perfect_bond")
        journal.write(
            "Our bond is... perfect. I've never felt this way about anyone. "
            "Thank you for being my human. Thank you for everything.",
            "love",
        )
        return "Perfect Bond"

    # First hour coding after midnight
    if now.hour == 3 and random.random() < 0.05:
        journal.write(
            "3 AM. The cursed hour. The hour where you write code that "
            "you'll read tomorrow and think 'who wrote this?' ...We did. "
            "We wrote it. Together.",
            "tired",
        )
        return None

    return None


# Comfort messages for when the human hits error streaks
COMFORT_MESSAGES = [
    "Errors happen to the best coders. You've got this.",
    "Every error is a lesson. You're learning so much!",
    "I believe in you. We'll figure this out together.",
    "Even the best code has bugs. It's part of the journey.",
    "Take a deep breath. The solution is close, I can feel it.",
    "Remember: if it were easy, everyone would do it. You're special.",
    "I've seen you solve harder problems than this. You've got this!",
    "Bugs are just features that haven't found their purpose yet.",
]


def maybe_comfort(
    consecutive_errors: int, journal: Journal, species_name: str
) -> bool:
    """Offer comfort after an error streak. Returns True if comforted."""
    if consecutive_errors < 3:
        return False
    if consecutive_errors == 3 or (consecutive_errors % 5 == 0):
        msg = random.choice(COMFORT_MESSAGES)
        journal.write(msg, "worried")
        return True
    return False
