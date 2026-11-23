from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.config import ROBOT_SIGNAL_TIMEOUT_SECONDS
from app.robot.router import router as robot_router
from app.robot.service import RobotConnection, RobotSignalState
from app.web.router import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.robot_signal = RobotSignalState(
        timeout_seconds=ROBOT_SIGNAL_TIMEOUT_SECONDS
    )
    app.state.robot_connection = RobotConnection()
    yield


app = FastAPI(title="Gureumi Backend", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(robot_router)
app.include_router(web_router)
