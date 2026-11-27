import asyncio
import logging
from json import JSONDecodeError

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.config import STATUS_SEND_INTERVAL_SECONDS
from app.robot.schemas import MotorCommand
from app.robot.service import (
    RobotConnection,
    RobotControlState,
    RobotSignalState,
    RobotUnavailableError,
)
from app.web.schemas import RobotConnectionStatus, WebMotorCommand

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

TEMP_USER_ID = "temp-user"


@router.websocket("/ws/robot-status")
async def provide_robot_status(websocket: WebSocket) -> None:
    state: RobotSignalState = websocket.app.state.robot_signal
    control: RobotControlState = websocket.app.state.robot_control
    await websocket.accept()

    try:
        while True:
            message = RobotConnectionStatus(
                jetson_status=state.current_status(),
                control_holder=control.holder(),
            )
            await websocket.send_json(message.model_dump())

            try:
                async with asyncio.timeout(STATUS_SEND_INTERVAL_SECONDS):
                    while True:
                        event = await websocket.receive()
                        if event["type"] == "websocket.disconnect":
                            return
            except TimeoutError:
                continue
    except (WebSocketDisconnect, OSError):
        return


@router.websocket("/ws/robot-command")
async def receive_motor_command(websocket: WebSocket) -> None:
    connection: RobotConnection = websocket.app.state.robot_connection
    control: RobotControlState = websocket.app.state.robot_control
    await websocket.accept()

    user_id = TEMP_USER_ID
    control.acquire(user_id)

    try:
        while True:
            try:
                data = await websocket.receive_json()
                request = WebMotorCommand.model_validate(data)
            except (JSONDecodeError, KeyError, ValidationError):
                continue

            if not control.acquire(user_id):
                continue

            if request.command == "stop":
                logger.info("web.stop_requested")
                continue

            command = MotorCommand.model_validate(request.model_dump())
            try:
                await connection.send_command(command)
            except RobotUnavailableError:
                continue
    except (WebSocketDisconnect, OSError):
        return
    finally:
        control.release(user_id)
