"""
Transparent HTTP proxy that intercepts LLM API SSE streams.
Sits between client and backend, observes traffic, maps to buddy states.
Does not modify any data - purely observational.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Callable

from aiohttp import web, ClientSession, ClientTimeout

from .providers.base import BaseProvider, StreamEvent, StreamPhase

logger = logging.getLogger("critter.proxy")


class ProxyServer:
    """
    Transparent HTTP reverse proxy for a single LLM API backend.
    Forwards all requests unchanged, intercepts SSE response streams,
    and emits StreamEvents through a callback for buddy reactions.
    """

    def __init__(
        self,
        backend_name: str,
        backend_url: str,
        provider: BaseProvider,
        listen_port: int = 9999,
        on_event: Callable[[str, str, StreamEvent], None] | None = None,
    ):
        self.backend_name = backend_name
        self.backend_url = backend_url.rstrip("/")
        self.provider = provider
        self.listen_port = listen_port
        self._on_event = on_event  # callback(session_id, backend_name, event)
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._client: ClientSession | None = None

    async def start(self):
        """Start the proxy server."""
        self._client = ClientSession(
            timeout=ClientTimeout(total=600, sock_read=300)
        )
        self._app = web.Application()
        self._app.router.add_route("*", "/{path:.*}", self._handle_request)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", self.listen_port)
        await site.start()
        logger.info(
            "Proxy [%s] listening on 127.0.0.1:%d -> %s",
            self.backend_name, self.listen_port, self.backend_url,
        )

    async def stop(self):
        """Stop the proxy server and clean up."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        if self._client:
            await self._client.close()
            self._client = None
        logger.info("Proxy [%s] stopped", self.backend_name)

    async def _handle_request(self, request: web.Request) -> web.StreamResponse:
        """Forward a request to the backend and intercept SSE streams."""
        # Build target URL
        path = request.match_info["path"]
        target_url = f"{self.backend_url}/{path}"
        if request.query_string:
            target_url += f"?{request.query_string}"

        # Forward headers (strip hop-by-hop headers)
        headers = {}
        skip = {"host", "transfer-encoding", "connection"}
        for key, value in request.headers.items():
            if key.lower() not in skip:
                headers[key] = value

        body = await request.read()

        # Each request gets a unique proxy session ID
        session_id = f"proxy-{uuid.uuid4().hex[:12]}"

        # Fresh provider instance per request (stateful parsers)
        provider = self.provider.__class__()

        # Signal stream start
        self._emit(session_id, provider.on_stream_start())

        try:
            async with self._client.request(
                request.method,
                target_url,
                headers=headers,
                data=body,
                allow_redirects=False,
            ) as upstream:
                content_type = upstream.headers.get("Content-Type", "")
                is_sse = "text/event-stream" in content_type

                # Build downstream response with upstream headers
                resp_headers = {
                    k: v
                    for k, v in upstream.headers.items()
                    if k.lower() not in ("transfer-encoding", "connection")
                }
                response = web.StreamResponse(
                    status=upstream.status, headers=resp_headers
                )
                await response.prepare(request)

                if is_sse:
                    await self._stream_sse(
                        upstream, response, session_id, provider
                    )
                else:
                    # Non-SSE: forward body chunks transparently
                    async for chunk in upstream.content.iter_any():
                        await response.write(chunk)

                # Signal stream end
                self._emit(session_id, provider.on_stream_end())

                await response.write_eof()
                return response

        except Exception as e:
            logger.error("Proxy [%s] error: %s", self.backend_name, e)
            self._emit(session_id, provider.on_stream_error(str(e)))
            return web.Response(status=502, text=f"Proxy error: {e}")

    async def _stream_sse(
        self,
        upstream,
        response: web.StreamResponse,
        session_id: str,
        provider: BaseProvider,
    ):
        """Stream SSE data to client while parsing lines through the provider."""
        buffer = ""
        async for chunk in upstream.content.iter_any():
            # Forward raw data to client unchanged
            await response.write(chunk)

            # Parse SSE lines for buddy state
            text = chunk.decode("utf-8", errors="replace")
            buffer += text

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                event = provider.parse_sse_line(line)
                if event:
                    self._emit(session_id, event)

    def _emit(self, session_id: str, event: StreamEvent):
        """Emit a stream event through the callback."""
        if self._on_event:
            try:
                self._on_event(session_id, self.backend_name, event)
            except Exception:
                logger.exception("Error in proxy event callback")
