"""
Idle behaviors and tool reactions for the critter companion.
Makes the critter feel alive between and during coding sessions.
"""

from __future__ import annotations

import random
from enum import Enum

from .mood import Mood


class IdleBehavior(str, Enum):
    """Distinct idle behaviors the critter can exhibit."""

    NORMAL = "normal"         # Standard idle animation
    LOOK_AROUND = "look"      # Eyes scan left and right
    DOZE = "doze"             # Brief sleep, eyes close
    DANCE = "dance"           # Happy little wiggle
    STRETCH = "stretch"       # Stretch and settle
    CURIOUS = "curious"       # Peek at something intently
    DAYDREAM = "daydream"     # Zoning out, thought bubble
    FIDGET = "fidget"         # Nervous shifting


# Mood -> weighted behavior pool: (behavior, weight)
MOOD_BEHAVIORS: dict[Mood, list[tuple[IdleBehavior, int]]] = {
    Mood.HAPPY: [
        (IdleBehavior.NORMAL, 25),
        (IdleBehavior.DANCE, 35),
        (IdleBehavior.LOOK_AROUND, 20),
        (IdleBehavior.CURIOUS, 20),
    ],
    Mood.CONTENT: [
        (IdleBehavior.NORMAL, 50),
        (IdleBehavior.LOOK_AROUND, 20),
        (IdleBehavior.STRETCH, 15),
        (IdleBehavior.CURIOUS, 15),
    ],
    Mood.CURIOUS: [
        (IdleBehavior.CURIOUS, 40),
        (IdleBehavior.LOOK_AROUND, 30),
        (IdleBehavior.NORMAL, 20),
        (IdleBehavior.FIDGET, 10),
    ],
    Mood.WORRIED: [
        (IdleBehavior.FIDGET, 40),
        (IdleBehavior.LOOK_AROUND, 30),
        (IdleBehavior.NORMAL, 20),
        (IdleBehavior.STRETCH, 10),
    ],
    Mood.TIRED: [
        (IdleBehavior.DOZE, 40),
        (IdleBehavior.STRETCH, 30),
        (IdleBehavior.NORMAL, 20),
        (IdleBehavior.DAYDREAM, 10),
    ],
    Mood.EXCITED: [
        (IdleBehavior.DANCE, 40),
        (IdleBehavior.CURIOUS, 30),
        (IdleBehavior.LOOK_AROUND, 20),
        (IdleBehavior.NORMAL, 10),
    ],
    Mood.SLEEPY: [
        (IdleBehavior.DOZE, 60),
        (IdleBehavior.STRETCH, 15),
        (IdleBehavior.DAYDREAM, 15),
        (IdleBehavior.NORMAL, 10),
    ],
    Mood.PROUD: [
        (IdleBehavior.DANCE, 35),
        (IdleBehavior.NORMAL, 35),
        (IdleBehavior.LOOK_AROUND, 15),
        (IdleBehavior.STRETCH, 15),
    ],
    Mood.NERVOUS: [
        (IdleBehavior.FIDGET, 50),
        (IdleBehavior.LOOK_AROUND, 30),
        (IdleBehavior.NORMAL, 15),
        (IdleBehavior.STRETCH, 5),
    ],
    Mood.BORED: [
        (IdleBehavior.DAYDREAM, 40),
        (IdleBehavior.STRETCH, 25),
        (IdleBehavior.DOZE, 20),
        (IdleBehavior.NORMAL, 15),
    ],
    Mood.LOVE: [
        (IdleBehavior.DANCE, 40),
        (IdleBehavior.NORMAL, 30),
        (IdleBehavior.LOOK_AROUND, 15),
        (IdleBehavior.CURIOUS, 15),
    ],
}


def pick_idle_behavior(mood: Mood) -> IdleBehavior:
    """Pick a random idle behavior, weighted by current mood."""
    pool = MOOD_BEHAVIORS.get(mood, [(IdleBehavior.NORMAL, 100)])
    behaviors, weights = zip(*pool)
    return random.choices(behaviors, weights=weights, k=1)[0]


# How behaviors modify the face on each tick
def apply_behavior_to_face(
    base_face: str, behavior: IdleBehavior, eye_char: str, tick: int
) -> str:
    """Modify the face string based on the current idle behavior and tick."""
    match behavior:
        case IdleBehavior.LOOK_AROUND:
            # Eyes shift direction every few ticks
            phase = tick % 6
            if phase < 2:
                return base_face  # center
            if phase < 4:
                # Shift eyes right by replacing eye with space+eye
                return base_face.replace(eye_char, " ", 1)
            return base_face  # back to center

        case IdleBehavior.DOZE:
            # Eyes close periodically
            if tick % 4 < 2:
                return base_face.replace(eye_char, "-")
            return base_face

        case IdleBehavior.DANCE:
            # Add bouncy suffixes
            bounces = ["~", " ~", "~", ""]
            return base_face + bounces[tick % len(bounces)]

        case IdleBehavior.STRETCH:
            if tick % 6 < 2:
                return base_face.replace(eye_char, "~")  # squint
            return base_face

        case IdleBehavior.CURIOUS:
            # One eye wider - replace second eye with O
            parts = base_face.rsplit(eye_char, 1)
            if len(parts) == 2:
                return parts[0] + eye_char + "O".join(parts[1:])
            return base_face + "?"

        case IdleBehavior.DAYDREAM:
            clouds = ["  .", " ..", "...", " ..", "  ."]
            return base_face + clouds[tick % len(clouds)]

        case IdleBehavior.FIDGET:
            # Rapid alternation
            if tick % 2:
                return base_face + ";"
            return base_face

        case _:
            return base_face


# Tool name -> what the critter is doing (for journal flavor text)
TOOL_REACTIONS: dict[str, str] = {
    "Read": "reading a file intently",
    "Edit": "watching edits carefully",
    "Write": "scribbling along",
    "Bash": "nervously watching the terminal",
    "Grep": "searching through the code",
    "Glob": "looking for files",
    "Agent": "excited about a new helper arriving",
    "WebSearch": "peering out at the internet",
    "WebFetch": "fetching something from far away",
    "TodoWrite": "checking items off a list",
}


def get_tool_reaction(tool_name: str) -> str | None:
    """Get a flavor-text reaction for a tool, or None."""
    for key, reaction in TOOL_REACTIONS.items():
        if key.lower() in tool_name.lower():
            return reaction
    return None
