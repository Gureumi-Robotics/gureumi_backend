import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.robot.schemas import MotorCommand
from app.robot.service import RobotUnavailableError
from app.web.schemas import WebMotorCommand
from helpers import run_commands


def test_stop_is_web_only():
    data = {"type": "motor_command", "command": "stop"}
    assert WebMotorCommand.model_validate(data).command == "stop"
    with pytest.raises(ValidationError):
        MotorCommand.model_validate(data)


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
