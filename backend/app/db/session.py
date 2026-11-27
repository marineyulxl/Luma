"""同步数据库连接与事务边界；由调用方管理 Engine 生命周期。"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.url(), pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def transaction(factory: sessionmaker[Session]) -> Iterator[Session]:
    """一个用例一个事务：成功提交、异常回滚，退出始终关闭 Session。"""
    with factory.begin() as session:
        yield session
