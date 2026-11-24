import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect
from pydantic import ValidationError

from app.robot.schemas import MotorCommand
from app.robot.service import RobotUnavailableError
from app.web.router import receive_motor_command
from app.web.schemas import WebMotorCommand


def test_stop_is_web_only():
    data = {"type": "motor_command", "command": "stop"}
    assert WebMotorCommand.model_validate(data).command == "stop"
    with pytest.raises(ValidationError):
        MotorCommand.model_validate(data)


def run_commands(messages, connection):
    websocket = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(robot_connection=connection)),
        accept=AsyncMock(),
        receive_json=AsyncMock(side_effect=[*messages, WebSocketDisconnect()]),
    )
    asyncio.run(receive_motor_command(websocket))
    websocket.accept.assert_awaited_once()


def test_stop_is_logged_but_only_forward_reaches_robot(caplog):
    connection = SimpleNamespace(send_command=AsyncMock())
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        run_commands(
            [
                {"type": "motor_command", "command": "stop"},
                {"type": "motor_command", "command": "forward"},
            ],
            connection,
        )
    connection.send_command.assert_awaited_once()
    assert connection.send_command.await_args.args[0].model_dump(mode="json") == {
        "type": "motor_command",
        "command": "forward",
    }
    assert "web.stop_requested" in caplog.text


def test_invalid_command_and_unavailable_robot_do_not_close_web_connection():
    connection = SimpleNamespace(
        send_command=AsyncMock(side_effect=RobotUnavailableError())
    )
    run_commands(
        [
            {"type": "motor_command", "command": "unknown"},
            {"type": "motor_command", "command": "forward"},
            {"type": "motor_command", "command": "stop"},
            {"type": "motor_command", "command": "forward"},
        ],
        connection,
    )
    assert connection.send_command.await_count == 2
