import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.robot.service import RobotControlState
from app.web.router import provide_robot_status


def run_status(jetson_status, control):
    websocket = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                robot_signal=SimpleNamespace(current_status=lambda: jetson_status),
                robot_control=control,
            )
        ),
        accept=AsyncMock(),
        send_json=AsyncMock(),
        receive=AsyncMock(return_value={"type": "websocket.disconnect"}),
    )
    asyncio.run(provide_robot_status(websocket))
    websocket.accept.assert_awaited_once()
    return websocket.send_json.await_args.args[0]


def test_status_includes_control_holder():
    control = RobotControlState(timeout_seconds=60.0)
    control.acquire("jisoo")

    message = run_status(1, control)

    assert message == {"jetson_status": 1, "control_holder": "jisoo"}


def test_control_holder_is_none_when_nobody_holds_it():
    control = RobotControlState(timeout_seconds=60.0)

    message = run_status(0, control)

    assert message == {"jetson_status": 0, "control_holder": None}


def test_control_holder_is_none_after_expiry():
    now = [0.0]
    control = RobotControlState(timeout_seconds=60.0, clock=lambda: now[0])
    control.acquire("jisoo")
    now[0] = 61.0

    message = run_status(1, control)

    assert message == {"jetson_status": 1, "control_holder": None}
