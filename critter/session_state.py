"""
Session state models - phase machine, session state, permission context.
Ported from Buddi's SessionPhase.swift + SessionState.swift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Permission context
# ---------------------------------------------------------------------------

@dataclass
class PermissionContext:
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any] | None
    received_at: datetime

    @property
    def formatted_input(self) -> str | None:
        if not self.tool_input:
            return None
        parts: list[str] = []
        for key, value in self.tool_input.items():
            if isinstance(value, str):
                display = value[:100] + "..." if len(value) > 100 else value
            elif isinstance(value, bool):
                display = "true" if value else "false"
            elif isinstance(value, (int, float)):
                display = str(value)
            else:
                display = "..."
            parts.append(f"{key}: {display}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Session phase (state machine)
# ---------------------------------------------------------------------------

class PhaseKind(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_INPUT = "waitingForInput"
    WAITING_FOR_APPROVAL = "waitingForApproval"
    COMPACTING = "compacting"
    ENDED = "ended"


@dataclass
class SessionPhase:
    kind: PhaseKind
    permission: PermissionContext | None = None

    # Convenience constructors
    @staticmethod
    def idle() -> SessionPhase:
        return SessionPhase(PhaseKind.IDLE)

    @staticmethod
    def processing() -> SessionPhase:
        return SessionPhase(PhaseKind.PROCESSING)

    @staticmethod
    def waiting_for_input() -> SessionPhase:
        return SessionPhase(PhaseKind.WAITING_FOR_INPUT)

    @staticmethod
    def waiting_for_approval(ctx: PermissionContext) -> SessionPhase:
        return SessionPhase(PhaseKind.WAITING_FOR_APPROVAL, permission=ctx)

    @staticmethod
    def compacting() -> SessionPhase:
        return SessionPhase(PhaseKind.COMPACTING)

    @staticmethod
    def ended() -> SessionPhase:
        return SessionPhase(PhaseKind.ENDED)

    # State machine transition validation
    def can_transition(self, to: SessionPhase) -> bool:
        cur = self.kind
        nxt = to.kind

        if cur == PhaseKind.ENDED:
            return False
        if nxt == PhaseKind.ENDED:
            return True

        valid: dict[PhaseKind, set[PhaseKind]] = {
            PhaseKind.IDLE: {
                PhaseKind.PROCESSING,
                PhaseKind.WAITING_FOR_INPUT,
                PhaseKind.WAITING_FOR_APPROVAL,
                PhaseKind.COMPACTING,
            },
            PhaseKind.PROCESSING: {
                PhaseKind.WAITING_FOR_INPUT,
                PhaseKind.WAITING_FOR_APPROVAL,
                PhaseKind.COMPACTING,
                PhaseKind.IDLE,
            },
            PhaseKind.WAITING_FOR_INPUT: {
                PhaseKind.PROCESSING,
                PhaseKind.IDLE,
                PhaseKind.COMPACTING,
            },
            PhaseKind.WAITING_FOR_APPROVAL: {
                PhaseKind.PROCESSING,
                PhaseKind.IDLE,
                PhaseKind.WAITING_FOR_INPUT,
                PhaseKind.WAITING_FOR_APPROVAL,
            },
            PhaseKind.COMPACTING: {
                PhaseKind.PROCESSING,
                PhaseKind.IDLE,
                PhaseKind.WAITING_FOR_INPUT,
            },
        }

        allowed = valid.get(cur, set())
        if nxt in allowed:
            return True
        # Allow staying in same state
        return cur == nxt

    @property
    def needs_attention(self) -> bool:
        return self.kind in (
            PhaseKind.WAITING_FOR_APPROVAL,
            PhaseKind.WAITING_FOR_INPUT,
        )

    @property
    def is_active(self) -> bool:
        return self.kind in (PhaseKind.PROCESSING, PhaseKind.COMPACTING)

    def __str__(self) -> str:
        if self.kind == PhaseKind.WAITING_FOR_APPROVAL and self.permission:
            return f"waitingForApproval({self.permission.tool_name})"
        return self.kind.value


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

class SessionSource(str, Enum):
    """Where this session originated from."""
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    HERMES = "hermes"
    PROXY = "proxy"


@dataclass
class SessionState:
    session_id: str
    cwd: str
    project_name: str = ""
    pid: int | None = None
    tty: str | None = None
    phase: SessionPhase = field(default_factory=SessionPhase.idle)
    last_activity: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    source: SessionSource = SessionSource.CLAUDE_CODE
    backend_name: str | None = None
    model: str | None = None

    def __post_init__(self):
        if not self.project_name:
            if self.cwd:
                self.project_name = Path(self.cwd).name
            elif self.backend_name:
                self.project_name = self.backend_name
            else:
                self.project_name = "unknown"

    @property
    def needs_attention(self) -> bool:
        return self.phase.needs_attention

    @property
    def active_permission(self) -> PermissionContext | None:
        if self.phase.kind == PhaseKind.WAITING_FOR_APPROVAL:
            return self.phase.permission
        return None

    @property
    def display_title(self) -> str:
        return self.project_name

    @property
    def source_label(self) -> str:
        if self.source == SessionSource.PROXY and self.backend_name:
            return self.backend_name
        if self.source == SessionSource.CODEX:
            return "Codex"
        if self.source == SessionSource.HERMES:
            return "Hermes"
        return "Claude Code"


# ---------------------------------------------------------------------------
# Hook event (received from the Python hook over Unix socket)
# ---------------------------------------------------------------------------

@dataclass
class HookEvent:
    session_id: str
    cwd: str
    event: str
    status: str
    pid: int | None = None
    tty: str | None = None
    tool: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_use_id: str | None = None
    notification_type: str | None = None
    message: str | None = None

    @staticmethod
    def from_json(data: dict) -> HookEvent:
        return HookEvent(
            session_id=data.get("session_id", "unknown"),
            cwd=data.get("cwd", ""),
            event=data.get("event", ""),
            status=data.get("status", ""),
            pid=data.get("pid"),
            tty=data.get("tty"),
            tool=data.get("tool"),
            tool_input=data.get("tool_input"),
            tool_use_id=data.get("tool_use_id"),
            notification_type=data.get("notification_type"),
            message=data.get("message"),
        )

    @property
    def expects_response(self) -> bool:
        return self.event == "PermissionRequest" and self.status == "waiting_for_approval"

    def determine_phase(self) -> SessionPhase:
        if self.event == "PreCompact":
            return SessionPhase.compacting()

        if self.expects_response and self.tool:
            return SessionPhase.waiting_for_approval(PermissionContext(
                tool_use_id=self.tool_use_id or "",
                tool_name=self.tool,
                tool_input=self.tool_input,
                received_at=datetime.now(),
            ))

        if self.event == "Notification" and self.notification_type == "idle_prompt":
            return SessionPhase.idle()

        match self.status:
            case "waiting_for_input":
                return SessionPhase.waiting_for_input()
            case "running_tool" | "processing" | "starting":
                return SessionPhase.processing()
            case "compacting":
                return SessionPhase.compacting()
            case "ended":
                return SessionPhase.ended()
            case _:
                return SessionPhase.idle()
