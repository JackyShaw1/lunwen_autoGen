import asyncio
from typing import Any

from fastapi import WebSocket


class ProgressHub:
    """任务进度 WebSocket 订阅中心（内存）"""

    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = {}
        self._state: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, task_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._channels.setdefault(task_id, set()).add(ws)
            snapshot = self._state.get(task_id)
        if snapshot:
            try:
                await ws.send_json(snapshot)
            except Exception:
                async with self._lock:
                    self._channels.get(task_id, set()).discard(ws)
                return

    async def unsubscribe(self, task_id: str, ws: WebSocket) -> None:
        async with self._lock:
            if task_id in self._channels:
                self._channels[task_id].discard(ws)
                if not self._channels[task_id]:
                    del self._channels[task_id]

    async def publish(self, task_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            prev = self._state.get(task_id) or {}
            # 未带 stream 的进度帧保留上一帧 stream，避免轮询间隙右侧空白
            merged = {**prev, **message}
            if "stream" not in message and "stream" in prev:
                merged["stream"] = prev["stream"]
            self._state[task_id] = merged
            sockets = list(self._channels.get(task_id, set()))
            out = merged
        for ws in sockets:
            try:
                await ws.send_json(out)
            except Exception:
                pass

    def get_state(self, task_id: str) -> dict[str, Any] | None:
        return self._state.get(task_id)


progress_hub = ProgressHub()
