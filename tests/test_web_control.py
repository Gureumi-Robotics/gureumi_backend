import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.robot.service import RobotControlState
from helpers import run_commands


def test_command_without_control_is_not_forwarded():
    connection = SimpleNamespace(send_command=AsyncMock())
    control = RobotControlState(timeout_seconds=60.0)
    control.acquire("someone-else")

    run_commands(
        [{"type": "motor_command", "command": "forward"}], connection, control
    )

    connection.send_command.assert_not_awaited()
    assert control.holder() == "someone-else"


def test_stop_without_control_is_not_logged(caplog):
    connection = SimpleNamespace(send_command=AsyncMock())
    control = RobotControlState(timeout_seconds=60.0)
    control.acquire("someone-else")

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        run_commands(
            [{"type": "motor_command", "command": "stop"}], connection, control
        )

    assert "web.stop_requested" not in caplog.text


def test_control_is_released_when_socket_closes():
    connection = SimpleNamespace(send_command=AsyncMock())
    control = RobotControlState(timeout_seconds=60.0)

    run_commands(
        [{"type": "motor_command", "command": "forward"}], connection, control
    )

    assert control.holder() is None
