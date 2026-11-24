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


class RobotControlState:
    def __init__(
        self,
        timeout_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")

        self.timeout_seconds = timeout_seconds
        self._clock = clock
        self._holder: str | None = None
        self._expires_at: float | None = None

    def holder(self) -> str | None:
        if self._holder is None or self._expires_at is None:
            return None

        if self._clock() >= self._expires_at:
            return None

        return self._holder

    def is_holder(self, user_id: str) -> bool:
        return self.holder() == user_id

    def acquire(self, user_id: str) -> bool:
        current = self.holder()

        if current is None and self._holder is not None:
            logger.info("robot.control_expired user=%s", self._holder)

        if current is not None and current != user_id:
            return False

        if current != user_id:
            logger.info("robot.control_acquired user=%s", user_id)

        self._holder = user_id
        self._expires_at = self._clock() + self.timeout_seconds
        return True

    def release(self, user_id: str) -> None:
        if self._holder != user_id:
            return

        self._holder = None
        self._expires_at = None
        logger.info("robot.control_released user=%s", user_id)
