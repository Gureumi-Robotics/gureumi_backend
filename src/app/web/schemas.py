from typing import Literal

from pydantic import BaseModel


class RobotConnectionStatus(BaseModel):
    jetson_status: Literal[0, 1]
    control_holder: str | None = None


class WebMotorCommand(BaseModel):
    type: Literal["motor_command"]
    command: Literal["forward", "stop"]
