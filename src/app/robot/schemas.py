from pydantic import BaseModel, Field


class JetsonHeartbeat(BaseModel):
    jetson_status: int = Field(strict=True, ge=1, le=1)
