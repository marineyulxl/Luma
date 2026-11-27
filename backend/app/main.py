"""应用工厂：启动时配置资源，关闭时释放连接池。"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.dependencies import DatabaseResources
from app.api.health import router as health_router
from app.api.schemas import ErrorDetail, ErrorResponse
from app.core.config import Settings
from app.db.session import build_engine, build_session_factory

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings.load()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(config)
        app.state.database = DatabaseResources(engine, build_session_factory(engine))
        try:
            yield
        finally:
            await run_in_threadpool(engine.dispose)

    production = config.app_env == "production"
    app = FastAPI(
        title="Luma API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if production else "/docs",
        redoc_url=None,
        openapi_url=None if production else "/openapi.json",
    )
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "Authorization"],
            allow_credentials=False,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        codes = {401: "unauthorized", 403: "forbidden", 404: "not_found", 503: "unavailable"}
        response = ErrorResponse(
            code=codes.get(error.status_code, "http_error"), message=str(error.detail)
        )
        return JSONResponse(
            status_code=error.status_code, content=response.model_dump(), headers=error.headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(field=".".join(str(part) for part in item["loc"]), message=item["msg"])
            for item in error.errors()
        ]
        response = ErrorResponse(
            code="validation_error", message="请求参数不符合要求", details=details
        )
        return JSONResponse(status_code=422, content=response.model_dump())

    @app.exception_handler(Exception)
    async def internal_error(request: Request, error: Exception) -> JSONResponse:
        logger.error("Unhandled API exception: %s", type(error).__name__)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(code="internal_error", message="服务处理失败").model_dump(),
        )

    app.include_router(health_router)
    return app
