"""Bound concurrent HTTP requests so database sessions stay within the pool."""

import asyncio

from starlette.types import ASGIApp, Receive, Scope, Send


class InFlightRequestLimitMiddleware:
    def __init__(self, app: ASGIApp, *, limit: int = 16) -> None:
        self.app = app
        self.slots = asyncio.Semaphore(limit)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        async with self.slots:
            await self.app(scope, receive, send)
