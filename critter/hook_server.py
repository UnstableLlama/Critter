"""
Unix domain socket server for receiving Claude Code hook events.
Ported from Buddi's HookSocketServer.swift.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import stat
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from .session_state import HookEvent

logger = logging.getLogger("critter.hooks")

SOCKET_PATH = "/tmp/critter.sock"
READ_TIMEOUT = 0.5  # seconds to wait for complete message
BUFFER_SIZE = 131072


@dataclass
class PendingPermission:
    session_id: str
    tool_use_id: str
    writer: asyncio.StreamWriter
    event: HookEvent
    received_at: datetime


class HookSocketServer:
    """Async Unix socket server that receives events from Claude Code hooks."""

    def __init__(self):
        self._server: asyncio.Server | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._on_event: Callable[[HookEvent], None] | None = None
        self._pending: dict[str, PendingPermission] = {}  # keyed by tool_use_id
        # Cache tool_use_id from PreToolUse → PermissionRequest correlation
        self._tool_id_cache: dict[str, list[str]] = {}

    async def start(self, on_event: Callable[[HookEvent], None]):
        self._on_event = on_event
        self._loop = asyncio.get_running_loop()

        # Remove stale socket
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass

        self._server = await asyncio.start_unix_server(
            self._handle_client, path=SOCKET_PATH
        )
        # Restrict permissions to owner only
        os.chmod(SOCKET_PATH, stat.S_IRUSR | stat.S_IWUSR)
        logger.info("Listening on %s", SOCKET_PATH)

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass
        # Close all pending permission sockets
        for pending in self._pending.values():
            pending.writer.close()
        self._pending.clear()

    def respond_to_permission(
        self, tool_use_id: str, decision: str, reason: str | None = None
    ):
        """Send a permission response. Safe to call from any thread."""
        if self._loop is None:
            logger.warning("Cannot respond: server not started")
            return
        asyncio.run_coroutine_threadsafe(
            self._send_response(tool_use_id, decision, reason), self._loop
        )

    def respond_by_session(
        self, session_id: str, decision: str, reason: str | None = None
    ):
        """Respond to the most recent pending permission for a session."""
        matching = [
            p for p in self._pending.values() if p.session_id == session_id
        ]
        if not matching:
            return
        most_recent = max(matching, key=lambda p: p.received_at)
        self.respond_to_permission(most_recent.tool_use_id, decision, reason)

    def cancel_pending(self, session_id: str):
        """Cancel all pending permissions for a session."""
        to_remove = [
            tid for tid, p in self._pending.items() if p.session_id == session_id
        ]
        for tid in to_remove:
            pending = self._pending.pop(tid)
            pending.writer.close()

    def cancel_specific(self, tool_use_id: str):
        """Cancel a specific pending permission (tool completed externally)."""
        pending = self._pending.pop(tool_use_id, None)
        if pending:
            pending.writer.close()

    def has_pending(self, session_id: str) -> bool:
        return any(p.session_id == session_id for p in self._pending.values())

    def get_pending(self, session_id: str) -> PendingPermission | None:
        for p in self._pending.values():
            if p.session_id == session_id:
                return p
        return None

    # ----- Cache for tool_use_id correlation -----

    def _cache_key(self, event: HookEvent) -> str:
        input_str = json.dumps(event.tool_input or {}, sort_keys=True)
        return f"{event.session_id}:{event.tool or 'unknown'}:{input_str}"

    def _cache_tool_id(self, event: HookEvent):
        if not event.tool_use_id:
            return
        key = self._cache_key(event)
        self._tool_id_cache.setdefault(key, []).append(event.tool_use_id)

    def _pop_cached_tool_id(self, event: HookEvent) -> str | None:
        key = self._cache_key(event)
        queue = self._tool_id_cache.get(key, [])
        if not queue:
            return None
        tool_id = queue.pop(0)
        if not queue:
            del self._tool_id_cache[key]
        return tool_id

    def _cleanup_cache(self, session_id: str):
        keys = [k for k in self._tool_id_cache if k.startswith(f"{session_id}:")]
        for k in keys:
            del self._tool_id_cache[k]

    # ----- Connection handling -----

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            data = b""
            try:
                data = await asyncio.wait_for(
                    reader.read(BUFFER_SIZE), timeout=READ_TIMEOUT
                )
            except asyncio.TimeoutError:
                pass

            if not data:
                writer.close()
                return

            try:
                raw = json.loads(data.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.warning("Failed to parse event")
                writer.close()
                return

            event = HookEvent.from_json(raw)
            logger.debug("Received: %s for %s", event.event, event.session_id[:8])

            # Cache tool_use_id from PreToolUse
            if event.event == "PreToolUse":
                self._cache_tool_id(event)

            if event.event == "SessionEnd":
                self._cleanup_cache(event.session_id)

            if event.expects_response:
                # Resolve tool_use_id
                tool_use_id = event.tool_use_id or self._pop_cached_tool_id(event)
                if not tool_use_id:
                    logger.warning(
                        "Permission request missing tool_use_id for %s",
                        event.session_id[:8],
                    )
                    writer.close()
                    if self._on_event:
                        self._on_event(event)
                    return

                # Update event with resolved tool_use_id
                event.tool_use_id = tool_use_id

                pending = PendingPermission(
                    session_id=event.session_id,
                    tool_use_id=tool_use_id,
                    writer=writer,
                    event=event,
                    received_at=datetime.now(),
                )

                # Replace any existing pending for same tool_use_id
                old = self._pending.pop(tool_use_id, None)
                if old:
                    old.writer.close()

                self._pending[tool_use_id] = pending

                if self._on_event:
                    self._on_event(event)
                return  # Keep socket open for response
            else:
                writer.close()

            if self._on_event:
                self._on_event(event)

        except Exception:
            logger.exception("Error handling client")
            try:
                writer.close()
            except Exception:
                pass

    async def _send_response(
        self, tool_use_id: str, decision: str, reason: str | None
    ):
        pending = self._pending.pop(tool_use_id, None)
        if not pending:
            logger.debug("No pending permission for %s", tool_use_id[:12])
            return

        response = {"decision": decision}
        if reason:
            response["reason"] = reason

        try:
            data = json.dumps(response).encode()
            pending.writer.write(data)
            await pending.writer.drain()
            pending.writer.close()
            logger.info(
                "Sent %s for %s tool:%s",
                decision,
                pending.session_id[:8],
                tool_use_id[:12],
            )
        except Exception:
            logger.exception("Failed to send permission response")
            try:
                pending.writer.close()
            except Exception:
                pass
