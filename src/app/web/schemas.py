from typing import Literal

from pydantic import BaseModel


class RobotConnectionStatus(BaseModel):
    jetson_status: Literal[0, 1]
