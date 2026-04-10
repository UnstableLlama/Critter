"""
OpenAI-compatible SSE stream parser.
Handles: OpenAI API, Ollama (/v1), llama.cpp, TabbyAPI.
"""

from __future__ import annotations

import json

from .base import BaseProvider, StreamEvent, StreamPhase


class OpenAIProvider(BaseProvider):
    """Parses OpenAI-format SSE streams (chat.completion.chunk)."""

    name = "openai"

    def __init__(self):
        self._has_tool_calls = False
        self._current_tool_name: str | None = None

    def parse_sse_line(self, line: str) -> StreamEvent | None:
        line = line.strip()

        # SSE format: "data: {json}" or "data: [DONE]"
        if not line.startswith("data:"):
            return None

        payload = line[5:].strip()

        if payload == "[DONE]":
            return StreamEvent(phase=StreamPhase.DONE)

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        return self._parse_chunk(data)

    def _parse_chunk(self, data: dict) -> StreamEvent | None:
        choices = data.get("choices", [])
        if not choices:
            # Usage-only chunk (stream_options.include_usage)
            usage = data.get("usage")
            if usage:
                return StreamEvent(phase=StreamPhase.DONE, usage=usage)
            return None

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")
        model = data.get("model")

        # Check for tool calls
        tool_calls = delta.get("tool_calls")
        if tool_calls:
            self._has_tool_calls = True
            tc = tool_calls[0]
            func = tc.get("function", {})
            name = func.get("name")
            if name:
                self._current_tool_name = name
            return StreamEvent(
                phase=StreamPhase.TOOL_CALLING,
                model=model,
                tool_name=self._current_tool_name,
            )

        # Check for content
        content = delta.get("content")
        if content is not None:
            return StreamEvent(
                phase=StreamPhase.GENERATING,
                model=model,
                content_delta=content,
            )

        # Finish reason
        if finish_reason:
            if finish_reason == "tool_calls":
                return StreamEvent(
                    phase=StreamPhase.TOOL_CALLING,
                    model=model,
                    finish_reason=finish_reason,
                    tool_name=self._current_tool_name,
                )
            return StreamEvent(
                phase=StreamPhase.DONE,
                model=model,
                finish_reason=finish_reason,
            )

        # Role-only delta (first chunk) or empty delta
        return StreamEvent(phase=StreamPhase.PROCESSING, model=model)

    def on_stream_start(self) -> StreamEvent:
        self._has_tool_calls = False
        self._current_tool_name = None
        return super().on_stream_start()
