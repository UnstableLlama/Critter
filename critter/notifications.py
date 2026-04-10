"""
Desktop notifications for Critter.
Uses GLib/Gio notifications on Linux (works with XFCE, GNOME, etc.).
Notifications are gentle - they only fire for important moments.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger("critter.notify")


def send_notification(
    title: str,
    body: str,
    urgency: str = "normal",
) -> bool:
    """Send a desktop notification via notify-send (available on most Linux DEs).

    urgency: "low", "normal", or "critical"
    Returns True if notification was sent successfully.
    """
    try:
        subprocess.Popen(
            [
                "notify-send",
                "--app-name=Critter",
                f"--urgency={urgency}",
                title,
                body,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        logger.debug("notify-send not found, skipping notification")
        return False
    except Exception:
        logger.debug("Failed to send notification", exc_info=True)
        return False


# ---- Pre-built notification helpers ----

def notify_hungry(species_name: str):
    send_notification(
        f"Your {species_name} is hungry!",
        "Your critter needs feeding. Open Critter and press Feed!",
        urgency="normal",
    )


def notify_tired(species_name: str):
    send_notification(
        f"Your {species_name} is exhausted!",
        "Your critter needs rest. Open Critter and press Rest!",
        urgency="normal",
    )


def notify_lonely(species_name: str):
    send_notification(
        f"Your {species_name} misses you!",
        "It's been a while. Your critter could use some attention.",
        urgency="low",
    )


def notify_milestone(species_name: str, milestone_name: str):
    send_notification(
        f"Milestone: {milestone_name}!",
        f"Your {species_name} achieved a new milestone!",
        urgency="normal",
    )


def notify_growth(species_name: str, stage_name: str):
    send_notification(
        f"Your {species_name} grew up!",
        f"Your critter evolved to {stage_name} stage!",
        urgency="normal",
    )


def notify_permission_needed(project_name: str, tool_name: str):
    send_notification(
        f"Permission needed: {tool_name}",
        f"Claude Code in {project_name} needs your approval.",
        urgency="critical",
    )
