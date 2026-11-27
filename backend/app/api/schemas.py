"""API 共用的响应格式。"""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    details: list[ErrorDetail] = []
    current_version: int | None = None
    current_updated_at: AwareDatetime | None = None
