"""健康检查仅暴露状态，不返回数据库地址或异常详情。"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import SessionDep
from app.api.schemas import ErrorResponse, HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse, operation_id="health_live")
def live() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/ready",
    response_model=HealthResponse,
    operation_id="health_ready",
    responses={503: {"model": ErrorResponse, "description": "数据库暂不可用"}},
)
def ready(session: SessionDep) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="服务暂不可用") from None
    return HealthResponse()
