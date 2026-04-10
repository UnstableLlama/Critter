"""
Sprite animator - computes animation frame strings on a timer.
Integrates mood, idle behaviors, and the emotional life system.
Ported from Buddi's SpriteAnimator.swift + extended for Critter.
"""

from __future__ import annotations

from typing import Callable

from .behaviors import IdleBehavior, apply_behavior_to_face, pick_idle_behavior
from .identity import BuddyIdentity, Eye, Species, Task
from .mood import Mood
from .sprite_data import face, render_frame

# Idle blink/fidget sequence (original Buddi sequence)
_IDLE_SEQUENCE = [0, 0, 0, 0, 1, 0, 0, 0, -1, 0, 0, 2, 0, 0, 0]

# Tick interval per task (seconds)
TASK_INTERVALS: dict[Task, float] = {
    Task.IDLE: 0.5,
    Task.WORKING: 0.4,
    Task.READING: 0.8,
    Task.WAITING: 0.5,
    Task.COMPACTING: 0.4,
    Task.SLEEPING: 1.2,
    Task.ERROR: 0.5,
    Task.SUCCESS: 0.5,
}

# How often to pick a new idle behavior (in ticks)
BEHAVIOR_CYCLE_TICKS = 20


def _blink_face(f: str, eye: Eye) -> str:
    return f.replace(eye.value, "-")


def _sleep_face(f: str, eye: Eye) -> str:
    return f.replace(eye.value, "-")


def _error_face(f: str, eye: Eye) -> str:
    return f.replace(eye.value, "X")


def _shift_eye_right(f: str, eye: Eye) -> str:
    idx = f.find(eye.value)
    if idx < 0:
        return f
    return f[:idx] + " " + f[idx + len(eye.value) :]


def compute_frame(
    task: Task,
    tick: int,
    species: Species,
    eye: Eye,
    mood: Mood | None = None,
    behavior: IdleBehavior | None = None,
) -> str:
    """Compute the animated one-line face string for a given tick."""
    mood_eye = mood.eye_override if mood else None
    base = face(species, eye, mood_eye=mood_eye)

    match task:
        case Task.IDLE:
            # Apply mood-driven idle behavior if available
            if behavior and behavior != IdleBehavior.NORMAL:
                return apply_behavior_to_face(
                    base, behavior, mood_eye or eye.value, tick
                )
            # Default idle: blink sequence
            seq = _IDLE_SEQUENCE
            val = seq[tick % len(seq)]
            if val == -1:
                return _blink_face(base, eye)
            # Add mood suffix
            suffix = mood.face_suffix if mood else ""
            return base + suffix

        case Task.WORKING:
            cursor = "|" if tick % 2 == 0 else ""
            return base + cursor

        case Task.READING:
            phase = tick % 3
            if phase == 1:
                return _shift_eye_right(base, eye)
            return base

        case Task.WAITING:
            dots = "." * ((tick % 3) + 1)
            return base + dots

        case Task.COMPACTING:
            suffix = "~" if tick % 2 == 0 else "~~"
            return base + suffix

        case Task.SLEEPING:
            z_count = (tick % 3) + 1
            return _sleep_face(base, eye) + " " + ("z" * z_count)

        case Task.ERROR:
            return _error_face(base, eye)

        case Task.SUCCESS:
            return base + " \u2713"

    return base


def compute_one_line(
    task: Task, species: Species, eye: Eye, mood: Mood | None = None
) -> str:
    """Static one-line face with task suffix (no animation tick)."""
    mood_eye = mood.eye_override if mood else None
    base = face(species, eye, mood_eye=mood_eye)
    suffix = task.face_suffix
    if task == Task.SLEEPING:
        return _sleep_face(base, eye) + suffix
    if task == Task.ERROR:
        return _error_face(base, eye) + suffix
    # Add mood display
    mood_str = f" [{mood.display}]" if mood else ""
    return base + suffix + mood_str


class SpriteAnimator:
    """Manages animation state with mood and behavior integration."""

    def __init__(self, identity: BuddyIdentity):
        self.identity = identity
        self._task = Task.IDLE
        self._tick = 0
        self._success_countdown = 0
        self._on_frame: Callable[[str, str], None] | None = None
        self._timer_id: int | None = None
        self.frame_string = ""
        self.one_line = ""

        # Emotional life
        self._mood: Mood | None = None
        self._behavior: IdleBehavior = IdleBehavior.NORMAL
        self._behavior_ticks = 0

        self._update_frame()

    @property
    def task(self) -> Task:
        return self._task

    @task.setter
    def task(self, value: Task):
        if value == self._task:
            return
        self._task = value
        self._tick = 0
        self._success_countdown = 5 if value == Task.SUCCESS else 0
        self._behavior_ticks = 0  # Reset behavior on task change
        self._update_frame()
        self._restart_timer()

    @property
    def mood(self) -> Mood | None:
        return self._mood

    @mood.setter
    def mood(self, value: Mood | None):
        if value != self._mood:
            self._mood = value
            # Pick a new behavior when mood changes
            if value and self._task == Task.IDLE:
                self._behavior = pick_idle_behavior(value)
                self._behavior_ticks = 0
            self._update_frame()

    def set_callback(self, callback: Callable[[str, str], None]):
        """Set callback(frame_string, one_line) called on each frame update."""
        self._on_frame = callback

    def start(self):
        """Start the animation timer (requires GLib)."""
        self._restart_timer()

    def stop(self):
        """Stop the animation timer."""
        if self._timer_id is not None:
            from gi.repository import GLib

            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def _restart_timer(self):
        self.stop()
        from gi.repository import GLib

        interval_ms = int(TASK_INTERVALS.get(self._task, 0.5) * 1000)
        self._timer_id = GLib.timeout_add(interval_ms, self._on_tick)

    def _on_tick(self) -> bool:
        self._tick += 1

        if self._task == Task.SUCCESS:
            self._success_countdown -= 1
            if self._success_countdown <= 0:
                self.task = Task.IDLE
                return False  # timer replaced by idle timer

        # Cycle idle behaviors based on mood
        if self._task == Task.IDLE and self._mood:
            self._behavior_ticks += 1
            if self._behavior_ticks >= BEHAVIOR_CYCLE_TICKS:
                self._behavior = pick_idle_behavior(self._mood)
                self._behavior_ticks = 0

        self._update_frame()
        return True  # keep timer running

    def _update_frame(self):
        self.frame_string = compute_frame(
            self._task,
            self._tick,
            self.identity.species,
            self.identity.eye,
            mood=self._mood,
            behavior=self._behavior if self._task == Task.IDLE else None,
        )
        self.one_line = compute_one_line(
            self._task, self.identity.species, self.identity.eye, mood=self._mood
        )
        if self._on_frame:
            self._on_frame(self.frame_string, self.one_line)

    def render_body(self) -> list[str]:
        """Render the full multi-line body for the current frame."""
        mood_eye = self._mood.eye_override if self._mood else None
        return render_frame(
            self.identity.species,
            self.identity.eye,
            self.identity.hat,
            self._tick,
            mood_eye=mood_eye,
        )
