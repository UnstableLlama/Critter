"""
Anthropic Messages API SSE stream parser.
Handles the distinct event types: message_start, content_block_start/delta/stop, message_delta, message_stop.
"""

from __future__ import annotations

import json

from .base import BaseProvider, StreamEvent, StreamPhase


class AnthropicProvider(BaseProvider):
    """Parses Anthropic-format SSE streams."""

    name = "anthropic"

    def __init__(self):
        self._current_block_type: str | None = None
        self._current_tool_name: str | None = None

    def parse_sse_line(self, line: str) -> StreamEvent | None:
        line = line.strip()

        # Anthropic SSE has "event: <type>" and "data: <json>" lines.
        # We handle both - the proxy will feed us raw lines.
        if line.startswith("event:"):
            # Store event type for context but don't emit yet
            self._last_event_type = line[6:].strip()
            return None

        if not line.startswith("data:"):
            return None

        payload = line[5:].strip()
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        event_type = data.get("type", self._last_event_type if hasattr(self, "_last_event_type") else "")

        match event_type:
            case "message_start":
                msg = data.get("message", {})
                model = msg.get("model")
                return StreamEvent(phase=StreamPhase.PROCESSING, model=model)

            case "content_block_start":
                block = data.get("content_block", {})
                self._current_block_type = block.get("type")
                if self._current_block_type == "tool_use":
                    self._current_tool_name = block.get("name")
                    return StreamEvent(
                        phase=StreamPhase.TOOL_CALLING,
                        tool_name=self._current_tool_name,
                    )
                if self._current_block_type == "thinking":
                    return StreamEvent(phase=StreamPhase.PROCESSING)
                return StreamEvent(phase=StreamPhase.GENERATING)

            case "content_block_delta":
                delta = data.get("delta", {})
                delta_type = delta.get("type", "")

                if delta_type == "text_delta":
                    return StreamEvent(
                        phase=StreamPhase.GENERATING,
                        content_delta=delta.get("text"),
                    )
                if delta_type == "thinking_delta":
                    return StreamEvent(phase=StreamPhase.PROCESSING)
                if delta_type == "input_json_delta":
                    return StreamEvent(
                        phase=StreamPhase.TOOL_CALLING,
                        tool_name=self._current_tool_name,
                    )
                return None

            case "content_block_stop":
                self._current_block_type = None
                return None

            case "message_delta":
                delta = data.get("delta", {})
                stop_reason = delta.get("stop_reason")
                usage = data.get("usage")
                if stop_reason == "tool_use":
                    return StreamEvent(
                        phase=StreamPhase.TOOL_CALLING,
                        finish_reason="tool_use",
                        usage=usage,
                    )
                return StreamEvent(
                    phase=StreamPhase.DONE,
                    finish_reason=stop_reason,
                    usage=usage,
                )

            case "message_stop":
                return StreamEvent(phase=StreamPhase.DONE)

            case "error":
                error = data.get("error", {})
                return StreamEvent(
                    phase=StreamPhase.ERROR,
                    error_message=error.get("message", "Unknown error"),
                )

        return None

    def on_stream_start(self) -> StreamEvent:
        self._current_block_type = None
        self._current_tool_name = None
        self._last_event_type = ""
        return super().on_stream_start()
