"""自动化测试只允许使用开发配置，数据由各用例事务回滚。"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import Settings
from app.db.session import build_engine, build_session_factory
from app.modules.accounts.models import RefreshToken, SessionToken, User

if os.environ.get("APP_ENV", "development") != "development":
    raise pytest.UsageError("pytest 只允许在 development 环境运行，禁止使用生产配置")
os.environ["APP_ENV"] = "development"


@pytest.fixture
def owner_database():
    settings = Settings.load()
    if settings.app_env != "development" or settings.name != "luma_dev":
        pytest.fail("账号数据库测试只允许使用 luma_dev")
    schema = "owner_test_" + uuid4().hex
    admin_engine = build_engine(settings)
    engine = None
    try:
        with admin_engine.begin() as conn:
            conn.execute(CreateSchema(schema))
        engine = create_engine(
            settings.url(),
            connect_args={
                "options": f"-c search_path={schema} -c timezone=UTC -c lock_timeout=5000"
            },
        )
        with engine.begin() as conn:
            User.__table__.create(conn)
            SessionToken.__table__.create(conn)
            RefreshToken.__table__.create(conn)
        yield build_session_factory(engine), engine
    finally:
        if engine is not None:
            engine.dispose()
        with admin_engine.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True, if_exists=True))
        admin_engine.dispose()
