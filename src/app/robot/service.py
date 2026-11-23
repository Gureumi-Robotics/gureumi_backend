import asyncio
import logging
import math
import time
from typing import Callable, Literal

from fastapi import WebSocket, WebSocketDisconnect

from app.robot.schemas import JetsonHeartbeat, MotorCommand


logger = logging.getLogger("uvicorn.error")


class RobotSignalState:
    def __init__(
        self,
        timeout_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")

        self.timeout_seconds = timeout_seconds
        self._clock = clock
        self._last_received_at: float | None = None

    def record(self, signal: JetsonHeartbeat) -> None:
        self._last_received_at = self._clock()
        logger.info("robot.heartbeat_received jetson_status=%s", signal.jetson_status)

    def current_status(self) -> Literal[0, 1]:
        if self._last_received_at is None:
            return 0

        elapsed = self._clock() - self._last_received_at

        return 1 if elapsed < self.timeout_seconds else 0


class RobotUnavailableError(Exception):
    pass


class RobotConnection:
    def __init__(self) -> None:
        self._socket: WebSocket | None = None
        self._send_lock = asyncio.Lock()

    def register(self, websocket: WebSocket) -> bool:
        if self._socket is not None:
            return False

        self._socket = websocket
        return True

    def unregister(self, websocket: WebSocket) -> None:
        if self._socket is websocket:
            self._socket = None

    async def send_command(self, command: MotorCommand) -> None:
        async with self._send_lock:
            socket = self._socket
            if socket is None:
                raise RobotUnavailableError()

            try:
                await socket.send_json(command.model_dump(mode="json"))
            except (WebSocketDisconnect, OSError, RuntimeError) as exc:
                self.unregister(socket)
                raise RobotUnavailableError() from exc
