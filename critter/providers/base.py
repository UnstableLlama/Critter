"""
Base provider - defines the interface for parsing LLM API streams
and mapping them to buddy animation states.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class StreamPhase(str, Enum):
    """Phases detected from an LLM API stream."""
    IDLE = "idle"
    PROCESSING = "processing"
    GENERATING = "generating"
    TOOL_CALLING = "tool_calling"
    TOOL_EXECUTING = "tool_executing"
    WAITING = "waiting"
    ERROR = "error"
    DONE = "done"


@dataclass
class StreamEvent:
    """An event parsed from an SSE stream."""
    phase: StreamPhase
    model: str | None = None
    content_delta: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    error_message: str | None = None
    finish_reason: str | None = None
    usage: dict[str, int] | None = None


class BaseProvider:
    """Base class for LLM API stream parsers."""

    name: str = "base"

    def parse_sse_line(self, line: str) -> StreamEvent | None:
        """Parse a single SSE data line and return a StreamEvent, or None if not actionable."""
        raise NotImplementedError

    def on_stream_start(self) -> StreamEvent:
        """Called when a new request begins streaming."""
        return StreamEvent(phase=StreamPhase.PROCESSING)

    def on_stream_end(self) -> StreamEvent:
        """Called when the stream terminates."""
        return StreamEvent(phase=StreamPhase.DONE)

    def on_stream_error(self, error: str) -> StreamEvent:
        """Called on stream error."""
        return StreamEvent(phase=StreamPhase.ERROR, error_message=error)
