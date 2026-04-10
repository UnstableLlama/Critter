"""
Central session state manager.
Ported from Buddi's SessionStore.swift - simplified for the Linux port.
All state mutations flow through process().
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

from .session_state import HookEvent, PhaseKind, SessionPhase, SessionState

logger = logging.getLogger("critter.session")


class SessionStore:
    """Manages all active Claude Code sessions."""

    def __init__(self):
        self._sessions: dict[str, SessionState] = {}
        self._on_change: Callable[[], None] | None = None

    def set_on_change(self, callback: Callable[[], None]):
        """Set callback invoked whenever session state changes."""
        self._on_change = callback

    @property
    def sessions(self) -> list[SessionState]:
        return sorted(
            self._sessions.values(),
            key=lambda s: s.last_activity,
            reverse=True,
        )

    def session(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def process_hook(self, event: HookEvent):
        """Process a hook event - the main entry point for state mutations."""
        sid = event.session_id
        is_new = sid not in self._sessions

        session = self._sessions.get(sid) or SessionState(
            session_id=sid,
            cwd=event.cwd,
            project_name=Path(event.cwd).name if event.cwd else "unknown",
            pid=event.pid,
            tty=event.tty,
        )

        # Update metadata
        if event.pid is not None:
            session.pid = event.pid
        if event.tty:
            session.tty = event.tty.replace("/dev/", "")
        session.last_activity = datetime.now()

        # Handle session end
        if event.status == "ended":
            self._sessions.pop(sid, None)
            self._notify()
            return

        # State machine transition
        new_phase = event.determine_phase()
        if session.phase.can_transition(new_phase):
            session.phase = new_phase
        else:
            logger.debug(
                "Invalid transition: %s -> %s, ignoring",
                session.phase,
                new_phase,
            )

        self._sessions[sid] = session
        self._notify()

    def process_permission_approved(self, session_id: str, tool_use_id: str):
        session = self._sessions.get(session_id)
        if not session:
            return
        session.phase = SessionPhase.processing()
        session.last_activity = datetime.now()
        self._notify()

    def process_permission_denied(
        self, session_id: str, tool_use_id: str, reason: str | None = None
    ):
        session = self._sessions.get(session_id)
        if not session:
            return
        session.phase = SessionPhase.idle()
        session.last_activity = datetime.now()
        self._notify()

    def remove_session(self, session_id: str):
        self._sessions.pop(session_id, None)
        self._notify()

    def _notify(self):
        if self._on_change:
            self._on_change()
