from json import JSONDecodeError

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.robot.schemas import JetsonHeartbeat
from app.robot.service import RobotConnection, RobotSignalState

router = APIRouter()


@router.websocket("/ws/robot")
async def receive_robot_signal(websocket: WebSocket) -> None:
    state: RobotSignalState = websocket.app.state.robot_signal
    connection: RobotConnection = websocket.app.state.robot_connection
    await websocket.accept()

    if not connection.register(websocket):
        await websocket.close()
        return

    try:
        while True:
            try:
                data = await websocket.receive_json()
                signal = JetsonHeartbeat.model_validate(data)
            except (JSONDecodeError, KeyError, ValidationError):
                continue

            state.record(signal)
    except WebSocketDisconnect:
        return
    finally:
        connection.unregister(websocket)
