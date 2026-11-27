from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.config import ROBOT_SIGNAL_TIMEOUT_SECONDS, settings
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(robot_router)
app.include_router(web_router)
