"""通过真实 PostgreSQL 隔离 schema 验证认证 HTTP 与事务行为。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.api.dependencies import DatabaseResources
from app.core.config import Settings
from app.main import create_app
from app.modules.accounts import auth_service
from app.modules.accounts.models import RefreshToken, SessionToken, User
from app.modules.accounts.schemas import OwnerCreate
from app.modules.accounts.security import COOKIE_NAME, AuthError
from app.modules.accounts.service import initialize_owner

PASSWORD = "Local test password 42"
ORIGIN = {"Origin": "http://testserver"}


@pytest.fixture
def auth_client(owner_database):
    factory, engine = owner_database
    owner = initialize_owner(
        factory, OwnerCreate(username="owner", display_name="所有者", password=PASSWORD)
    )
    with TestClient(create_app()) as client:
        client.app.state.database = DatabaseResources(engine, factory)
        yield client, factory, owner


def login(client, password=PASSWORD):
    return client.post(
        "/api/auth/sessions", headers=ORIGIN, json={"username": "OWNER", "password": password}
    )


def authorization(token):
    return {"Authorization": "Bearer " + token}


def test_login_refresh_account_logout_round_trip(auth_client):
    client, factory, owner = auth_client
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["account"] == {"id": str(owner.id), "username": "owner", "display_name": "所有者"}
    assert body["token_type"] == "Bearer" and body["access_expires_in"] == 900
    assert response.headers["cache-control"] == "no-store"
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/api/auth/sessions" in cookie
    old_refresh = client.cookies[COOKIE_NAME]
    token = body["access_token"]
    assert client.get("/api/account", headers=authorization(token)).json() == body["account"]
    refreshed = client.post("/api/auth/sessions/refresh", headers=ORIGIN)
    assert refreshed.status_code == 200
    assert client.cookies[COOKIE_NAME] != old_refresh
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(SessionToken)) == 1
        assert session.scalar(select(func.count()).select_from(RefreshToken)) == 2
        assert session.scalar(select(RefreshToken.token_hash).limit(1)) != old_refresh
    response = client.delete("/api/auth/sessions/current", headers=authorization(token))
    assert response.status_code == 204 and response.content == b""
    assert COOKIE_NAME not in client.cookies
    assert client.get("/api/account", headers=authorization(token)).status_code == 401
    assert client.post("/api/auth/sessions/refresh", headers=ORIGIN).status_code == 401


def test_wrong_password_unknown_user_and_disabled_account_have_same_error(auth_client):
    client, factory, owner = auth_client
    incorrect = login(client, "wrong password")
    unknown = client.post(
        "/api/auth/sessions", headers=ORIGIN, json={"username": "unknown", "password": PASSWORD}
    )
    with factory.begin() as session:
        session.execute(
            update(User).where(User.id == owner.id).values(disabled_at=datetime.now(UTC))
        )
    disabled = login(client)
    assert incorrect.status_code == unknown.status_code == disabled.status_code == 401
    assert incorrect.json() == unknown.json() == disabled.json()
    assert incorrect.json()["code"] == "invalid_credentials"
    assert PASSWORD not in disabled.text
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(SessionToken)) == 0


def test_refresh_reuse_commits_revocation_and_preserves_other_session(auth_client):
    client, factory, _ = auth_client
    first = login(client).json()["access_token"]
    old_refresh = client.cookies[COOKIE_NAME]
    assert client.post("/api/auth/sessions/refresh", headers=ORIGIN).status_code == 200
    second = login(client).json()["access_token"]
    replay = client.post(
        "/api/auth/sessions/refresh", headers={**ORIGIN, "Cookie": COOKIE_NAME + "=" + old_refresh}
    )
    assert replay.status_code == 401
    assert client.get("/api/account", headers=authorization(first)).status_code == 401
    assert client.get("/api/account", headers=authorization(second)).status_code == 200
    with factory() as session:
        assert (
            session.scalar(
                select(SessionToken.revoked_reason).where(SessionToken.revoked_at.is_not(None))
            )
            == "refresh_reuse"
        )


def test_concurrent_refresh_has_one_success_then_revokes_chain(auth_client):
    client, factory, _ = auth_client
    token = login(client).json()["access_token"]
    refresh_value = client.cookies[COOKIE_NAME]
    barrier = Barrier(2)
    security = client.app.state.token_security

    def attempt(_):
        barrier.wait(timeout=5)
        try:
            auth_service.refresh_session(factory, security, refresh_value)
            return 200
        except AuthError:
            return 401

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(attempt, range(2))) == [200, 401]
    assert client.get("/api/account", headers=authorization(token)).status_code == 401
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(RefreshToken)) == 2


def test_failed_jwt_issuance_rolls_back_rotation(auth_client, monkeypatch):
    client, factory, _ = auth_client
    login(client)
    security = client.app.state.token_security
    value = client.cookies[COOKIE_NAME]

    def fail(*args):
        raise RuntimeError("signing failed")

    monkeypatch.setattr(security, "encode", fail)
    with pytest.raises(RuntimeError, match="signing failed"):
        auth_service.refresh_session(factory, security, value)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(RefreshToken)) == 1
        assert session.scalar(select(RefreshToken.consumed_at)) is None


@pytest.mark.parametrize("origin", [None, "null", "https://evil.example"])
def test_untrusted_origin_cannot_login_or_rotate(auth_client, origin):
    client, _, _ = auth_client
    login(client)
    value = client.cookies[COOKIE_NAME]
    headers = {} if origin is None else {"Origin": origin}
    assert (
        client.post(
            "/api/auth/sessions", headers=headers, json={"username": "owner", "password": PASSWORD}
        ).status_code
        == 403
    )
    assert client.post("/api/auth/sessions/refresh", headers=headers).status_code == 403
    assert client.delete("/api/auth/sessions/current", headers=headers).status_code == 403
    assert client.cookies[COOKIE_NAME] == value


@pytest.mark.parametrize(
    "kind",
    [
        "expired",
        "wrong_key",
        "wrong_issuer",
        "wrong_audience",
        "wrong_type",
        "missing_sid",
        "invalid_uuid",
        "none_algorithm",
    ],
)
def test_invalid_jwt_cannot_read_account(auth_client, kind):
    client, _, _ = auth_client
    token = login(client).json()["access_token"]
    settings = client.app.state.token_security.settings
    claims = jwt.decode(token, options={"verify_signature": False})
    key = settings.auth_signing_key.get_secret_value()
    algorithm = "HS256"
    if kind == "expired":
        claims["exp"] = 1
    if kind == "wrong_key":
        key = "wrong-key-for-tests-only-1234567890123"
    if kind == "wrong_issuer":
        claims["iss"] = "wrong"
    if kind == "wrong_audience":
        claims["aud"] = "wrong"
    if kind == "wrong_type":
        claims["type"] = "refresh"
    if kind == "missing_sid":
        del claims["sid"]
    if kind == "invalid_uuid":
        claims["sid"] = "not-a-uuid"
    if kind == "none_algorithm":
        key, algorithm = "", "none"
    invalid = jwt.encode(claims, key, algorithm=algorithm)
    response = client.get("/api/account", headers=authorization(invalid))
    assert response.status_code == 401 and response.json()["code"] == "unauthenticated"


def test_expired_access_can_logout_with_refresh_cookie(auth_client):
    client, _, _ = auth_client
    token = login(client).json()["access_token"]
    security = client.app.state.token_security
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["exp"] = 1
    expired = jwt.encode(
        claims, security.settings.auth_signing_key.get_secret_value(), algorithm="HS256"
    )
    assert (
        client.delete(
            "/api/auth/sessions/current", headers={**ORIGIN, **authorization(expired)}
        ).status_code
        == 204
    )
    assert client.get("/api/account", headers=authorization(token)).status_code == 401


@pytest.mark.parametrize("state", ["idle", "absolute", "disabled"])
def test_database_expiry_and_disable_invalidate_access_and_refresh(auth_client, state):
    client, factory, owner = auth_client
    token = login(client).json()["access_token"]
    now = datetime.now(UTC)
    with factory.begin() as session:
        if state == "disabled":
            session.execute(update(User).where(User.id == owner.id).values(disabled_at=now))
        else:
            values = dict(
                created_at=now - timedelta(days=40),
                last_refreshed_at=now - timedelta(days=8),
                idle_expires_at=now - timedelta(seconds=1),
            )
            if state == "absolute":
                values["expires_at"] = now - timedelta(seconds=1)
            session.execute(update(SessionToken).values(**values))
    assert client.get("/api/account", headers=authorization(token)).status_code == 401
    assert client.post("/api/auth/sessions/refresh", headers=ORIGIN).status_code == 401


def test_login_rate_limit_and_input_redaction(auth_client):
    client, _, _ = auth_client
    for _ in range(10):
        assert login(client, "wrong").status_code == 401
    response = login(client)
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
    invalid = client.post(
        "/api/auth/sessions",
        headers=ORIGIN,
        json={"username": "owner", "password": {"secret": PASSWORD}},
    )
    assert invalid.status_code == 422 and PASSWORD not in invalid.text


def test_production_cookie_is_secure_and_cors_supports_credentials(auth_client):
    client, _, _ = auth_client
    settings = client.app.state.token_security.settings
    client.app.state.token_security.settings = settings.model_copy(update={"app_env": "production"})
    assert "; Secure" in login(client).headers["set-cookie"]
    config = Settings.load().model_copy(update={"cors_origins": ["http://localhost:5173"]})
    with TestClient(create_app(config)) as cors_client:
        response = cors_client.options(
            "/api/auth/sessions",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
        )
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert response.headers["access-control-allow-credentials"] == "true"


def test_failed_login_signing_leaves_no_session(auth_client, monkeypatch):
    client, factory, _ = auth_client

    def fail(*args):
        raise RuntimeError("signing failed")

    monkeypatch.setattr(client.app.state.token_security, "encode", fail)
    with pytest.raises(RuntimeError, match="signing failed"):
        login(client)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(SessionToken)) == 0
        assert session.scalar(select(func.count()).select_from(RefreshToken)) == 0


def test_refresh_requires_cookie_and_expiry_is_capped_by_absolute_deadline(auth_client):
    client, factory, _ = auth_client
    token = login(client).json()["access_token"]
    value = client.cookies[COOKIE_NAME]
    client.cookies.clear()
    assert (
        client.post(
            "/api/auth/sessions/refresh", headers={**ORIGIN, **authorization(token)}
        ).status_code
        == 401
    )
    with factory.begin() as session:
        now = datetime.now(UTC)
        session.execute(
            update(SessionToken).values(
                expires_at=now + timedelta(seconds=120),
                idle_expires_at=now + timedelta(seconds=100),
            )
        )
    response = client.post(
        "/api/auth/sessions/refresh", headers={**ORIGIN, "Cookie": COOKIE_NAME + "=" + value}
    )
    assert response.status_code == 200
    assert 1 <= response.json()["access_expires_in"] <= 120
    with factory() as session:
        row = session.scalar(select(SessionToken))
        assert row.idle_expires_at == row.expires_at
    with factory.begin() as session:
        session.execute(
            update(RefreshToken)
            .where(RefreshToken.consumed_at.is_(None))
            .values(
                created_at=datetime.now(UTC) - timedelta(days=1),
                expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
    assert client.post("/api/auth/sessions/refresh", headers=ORIGIN).status_code == 401
