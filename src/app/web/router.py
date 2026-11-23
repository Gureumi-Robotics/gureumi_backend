import asyncio
from json import JSONDecodeError

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.config import STATUS_SEND_INTERVAL_SECONDS
from app.robot.schemas import MotorCommand
from app.robot.service import (
    RobotConnection,
    RobotSignalState,
    RobotUnavailableError,
)
from app.web.schemas import RobotConnectionStatus

router = APIRouter()


@router.websocket("/ws/robot-status")
async def provide_robot_status(websocket: WebSocket) -> None:
    state: RobotSignalState = websocket.app.state.robot_signal
    await websocket.accept()

    try:
        while True:
            message = RobotConnectionStatus(jetson_status=state.current_status())
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
    await websocket.accept()

    try:
        while True:
            try:
                data = await websocket.receive_json()
                command = MotorCommand.model_validate(data)
            except (JSONDecodeError, KeyError, ValidationError):
                continue

            try:
                await connection.send_command(command)
            except RobotUnavailableError:
                continue
    except (WebSocketDisconnect, OSError):
        return
