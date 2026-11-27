import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import WebSocketDisconnect

from app.robot.service import RobotControlState
from app.web.router import receive_motor_command


def run_commands(messages, connection, control=None):
    control = control or RobotControlState(timeout_seconds=60.0)
    websocket = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                robot_connection=connection,
                robot_control=control,
            )
        ),
        accept=AsyncMock(),
        receive_json=AsyncMock(side_effect=[*messages, WebSocketDisconnect()]),
    )
    asyncio.run(receive_motor_command(websocket))
    websocket.accept.assert_awaited_once()
