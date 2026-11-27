"""应用生命周期、健康检查、错误响应和契约边界。"""

from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import Settings
from app.main import create_app


def test_health_and_engine_lifecycle():
    app = create_app()
    assert not hasattr(app.state, "database")
    disposed = []
    with TestClient(app) as client:
        event.listen(
            app.state.database.engine, "engine_disposed", lambda engine: disposed.append(True)
        )
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").status_code == 200
        spec = client.get("/openapi.json").json()
        assert set(spec["paths"]) == {"/health/live", "/health/ready"}
        assert client.get("/api/contents").status_code == 404
    assert disposed == [True]


def test_database_error_response_hides_details():
    app = create_app()
    fake = Mock(spec=Session)
    fake.execute.side_effect = OperationalError("SQL", None, Exception("private-database-detail"))
    app.dependency_overrides[get_session] = lambda: fake
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["code"] == "unavailable"
    assert "private-database-detail" not in response.text


def test_production_hides_docs_without_contacting_database():
    settings = Settings(
        APP_ENV="production",
        DB_HOST="127.0.0.1",
        DB_PORT=5432,
        DB_NAME="luma",
        DB_USER="luma_app",
        DB_PASSWORD="test-only-long-secret",
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
