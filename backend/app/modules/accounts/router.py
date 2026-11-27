"""登录相关 HTTP 适配，业务事务由 auth_service 管理。"""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer

from app.api.business_schemas import AccountDetail, LoginRequest, SessionDetail
from app.api.dependencies import get_resources
from app.api.schemas import ErrorResponse
from app.modules.accounts import auth_service
from app.modules.accounts.security import (
    COOKIE_NAME,
    COOKIE_PATH,
    AccessIdentity,
    AuthError,
    RequestLimiter,
    TokenSecurity,
)

router = APIRouter(
    tags=["accounts"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 422, 429, 500)},
)
bearer = HTTPBearer(auto_error=False, scheme_name="accessToken", bearerFormat="JWT")
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
refresh_cookie = APIKeyCookie(name=COOKIE_NAME, auto_error=False, scheme_name="refreshCookie")
RefreshCredential = Annotated[str | None, Depends(refresh_cookie)]
origin_parameter = {
    "parameters": [
        {"name": "Origin", "in": "header", "required": True, "schema": {"type": "string"}}
    ]
}


def get_security(request: Request) -> TokenSecurity:
    return cast(TokenSecurity, request.app.state.token_security)


def require_identity(request: Request, credentials: Credentials) -> AccessIdentity:
    if credentials is None:
        raise AuthError()
    return get_security(request).decode(credentials.credentials)


def check_origin(request: Request) -> None:
    security = get_security(request)
    allowed = set(security.settings.cors_origins)
    allowed.add(str(request.base_url).rstrip("/"))
    if request.headers.get("origin") not in allowed:
        raise AuthError("forbidden", "请求来源不受信任", 403)


def limit_request(request: Request, scope: str, limit: int, seconds: int) -> None:
    limiter = cast(RequestLimiter, request.app.state.auth_limiter)
    address = request.client.host if request.client else "unknown"
    limiter.check(scope, "all", limit * 10, seconds)
    limiter.check(scope, address, limit, seconds)


def session_response(
    response: Response, result: auth_service.LoginResult, security: TokenSecurity
) -> SessionDetail:
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        COOKIE_NAME,
        result.refresh_value,
        max_age=result.cookie_seconds,
        httponly=True,
        secure=security.settings.app_env == "production",
        samesite="lax",
        path=COOKIE_PATH,
    )
    return result.detail


@router.post(
    "/api/auth/sessions",
    operation_id="sessions_create",
    response_model=SessionDetail,
    openapi_extra=origin_parameter,
)
def login(request: Request, body: LoginRequest, response: Response) -> SessionDetail:
    check_origin(request)
    limit_request(request, "login", 10, 300)
    security = get_security(request)
    result = auth_service.login_owner(get_resources(request).session_factory, security, body)
    return session_response(response, result, security)


@router.post(
    "/api/auth/sessions/refresh",
    operation_id="sessions_refresh",
    response_model=SessionDetail,
    openapi_extra=origin_parameter,
)
def refresh(request: Request, response: Response, value: RefreshCredential) -> SessionDetail:
    check_origin(request)
    limit_request(request, "refresh", 60, 60)
    security = get_security(request)
    result = auth_service.refresh_session(get_resources(request).session_factory, security, value)
    return session_response(response, result, security)


@router.get("/api/account", operation_id="account_detail", response_model=AccountDetail)
def account(
    request: Request,
    response: Response,
    identity: Annotated[AccessIdentity, Depends(require_identity)],
) -> AccountDetail:
    response.headers["Cache-Control"] = "no-store"
    return auth_service.current_account(get_resources(request).session_factory, identity)


@router.delete("/api/auth/sessions/current", operation_id="sessions_delete", status_code=204)
def logout(request: Request, credentials: Credentials, value: RefreshCredential) -> Response:
    identity = None
    if credentials is not None:
        try:
            candidate = get_security(request).decode(credentials.credentials)
            auth_service.current_account(get_resources(request).session_factory, candidate)
            identity = candidate
        except AuthError:
            pass  # Access Token 已过期时仍可通过有效刷新凭据退出。
    if identity is None:
        check_origin(request)
    auth_service.logout_session(get_resources(request).session_factory, identity, value)
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=get_security(request).settings.app_env == "production",
        samesite="lax",
    )
    return response
