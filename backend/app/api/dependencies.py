"""请求依赖负责 Session 生命周期，不在这里隐式提交事务。"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class DatabaseResources:
    engine: Engine
    session_factory: sessionmaker[Session]


def get_resources(request: Request) -> DatabaseResources:
    return cast(DatabaseResources, request.app.state.database)


def get_session(request: Request) -> Iterator[Session]:
    with get_resources(request).session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
