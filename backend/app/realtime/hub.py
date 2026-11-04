"""Deliver committed measurements from MQTT's thread to WebSocket clients."""

import asyncio
import logging
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class RealtimeHub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self.loop: asyncio.AbstractEventLoop | None = None
        self.task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.create_task(self._deliver())

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.loop = None

    def publish_from_thread(self, event: dict[str, Any]) -> None:
        if self.loop is None:
            return

        def enqueue() -> None:
            try:
                self.queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Realtime queue full; clients will catch up through HTTP polling")

        try:
            self.loop.call_soon_threadsafe(enqueue)
        except RuntimeError:
            pass  # Application is shutting down.

    async def _deliver(self) -> None:
        while True:
            event = await self.queue.get()
            if self.clients:
                clients = tuple(self.clients)
                results = await asyncio.gather(
                    *(asyncio.wait_for(client.send_json(event), timeout=2) for client in clients),
                    return_exceptions=True,
                )
                for client, result in zip(clients, results):
                    if isinstance(result, BaseException):
                        self.clients.discard(client)
            self.queue.task_done()
