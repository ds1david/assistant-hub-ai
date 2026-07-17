import asyncio
from collections.abc import Iterable

from fastapi import WebSocket


class TranscriptBroadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def publish(self, event: dict) -> None:
        async with self._lock:
            clients: Iterable[WebSocket] = tuple(self._clients)

        stale: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(event)
            except Exception:
                stale.append(client)

        if stale:
            async with self._lock:
                for client in stale:
                    self._clients.discard(client)
