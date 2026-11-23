from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class JetsonHeartbeat(BaseModel):
    jetson_status: int = Field(strict=True, ge=1, le=1)


class MotorAction(StrEnum):
    FORWARD = "forward"


class MotorCommand(BaseModel):
    type: Literal["motor_command"]
    command: MotorAction
