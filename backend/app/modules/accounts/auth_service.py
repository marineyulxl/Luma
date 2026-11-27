"""认证用例。写入统一按用户、会话、刷新令牌顺序加锁。"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.business_schemas import AccountDetail, LoginRequest, SessionDetail
from app.db.session import transaction
from app.modules.accounts.models import RefreshToken, SessionToken, User
from app.modules.accounts.security import AccessIdentity, AuthError, TokenSecurity, refresh_digest


@dataclass(frozen=True)
class LoginResult:
    detail: SessionDetail
    refresh_value: str
    cookie_seconds: int


def account_detail(user: User) -> AccountDetail:
    return AccountDetail(id=user.id, username=user.username, display_name=user.display_name)


def database_now(session: Session) -> datetime:
    return cast(datetime, session.execute(select(func.clock_timestamp())).scalar_one())


def is_active(user: User | None, login: SessionToken | None, now: datetime) -> bool:
    return bool(
        user is not None
        and user.disabled_at is None
        and login is not None
        and login.revoked_at is None
        and login.expires_at > now
        and login.idle_expires_at > now
    )


def issue_result(
    security: TokenSecurity, user: User, login: SessionToken, now: datetime
) -> LoginResult:
    access_token, lifetime = security.encode(
        user.id, login.id, now, min(login.expires_at, login.idle_expires_at)
    )
    return LoginResult(
        SessionDetail(
            account=account_detail(user),
            expires_at=min(login.expires_at, login.idle_expires_at),
            access_token=access_token,
            access_expires_in=lifetime,
        ),
        secrets.token_urlsafe(48),
        max(1, int((login.idle_expires_at - now).total_seconds())),
    )


def login_owner(
    factory: sessionmaker[Session], security: TokenSecurity, request: LoginRequest
) -> LoginResult:
    # 先读密码快照并释放连接，再进行较昂贵的 Argon2 校验。
    with factory() as session:
        candidate = session.scalar(
            select(User).where(func.lower(User.username) == func.lower(request.username))
        )
        owner_id = candidate.id if candidate else None
        old_hash = candidate.password_hash if candidate else None
    valid = security.verify_password(request.password.get_secret_value(), old_hash)
    if not valid or owner_id is None:
        raise AuthError("invalid_credentials", "账号或密码错误")
    with transaction(factory) as session:
        user = session.scalar(select(User).where(User.id == owner_id).with_for_update())
        if user is None or user.disabled_at is not None or user.password_hash != old_hash:
            raise AuthError("invalid_credentials", "账号或密码错误")
        now = database_now(session)
        expiry = now + timedelta(seconds=security.settings.session_max_seconds)
        login = SessionToken(
            id=uuid4(),
            owner_id=user.id,
            created_at=now,
            updated_at=now,
            expires_at=expiry,
            last_refreshed_at=now,
            idle_expires_at=min(
                expiry, now + timedelta(seconds=security.settings.refresh_idle_seconds)
            ),
        )
        session.add(login)
        session.flush()
        result = issue_result(security, user, login, now)
        session.add(
            RefreshToken(
                owner_id=user.id,
                session_id=login.id,
                created_at=now,
                expires_at=login.idle_expires_at,
                token_hash=refresh_digest(result.refresh_value),
            )
        )
    return result


def refresh_lookup(session: Session, value: str | None) -> tuple[UUID, UUID, UUID]:
    if not value or len(value) > 256:
        raise AuthError()
    row = session.execute(
        select(RefreshToken.owner_id, RefreshToken.session_id, RefreshToken.id).where(
            RefreshToken.token_hash == refresh_digest(value)
        )
    ).one_or_none()
    if row is None:
        raise AuthError()
    return row[0], row[1], row[2]


def locked_session(
    session: Session, owner_id: UUID, session_id: UUID
) -> tuple[User, SessionToken, datetime]:
    user = session.scalar(select(User).where(User.id == owner_id).with_for_update())
    login = session.scalar(
        select(SessionToken)
        .where(SessionToken.id == session_id, SessionToken.owner_id == owner_id)
        .with_for_update()
    )
    now = database_now(session)
    if user is None or login is None or not is_active(user, login, now):
        raise AuthError()
    return user, login, now


def refresh_session(
    factory: sessionmaker[Session], security: TokenSecurity, value: str | None
) -> LoginResult:
    result: LoginResult | None = None
    with transaction(factory) as session:
        owner_id, session_id, token_id = refresh_lookup(session, value)
        user, login, now = locked_session(session, owner_id, session_id)
        token = session.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.id == token_id,
                RefreshToken.owner_id == owner_id,
                RefreshToken.session_id == session_id,
            )
            .with_for_update()
        )
        if token is None:
            raise AuthError()
        if token.consumed_at is not None:
            login.revoked_at, login.revoked_reason, login.updated_at = now, "refresh_reuse", now
            # 必须先退出事务提交撤销，再向客户端返回 401。
        elif token.expires_at <= now:
            raise AuthError()
        else:
            token.consumed_at = now
            session.flush()  # 释放当前有效叶节点的部分唯一索引位置。
            login.last_refreshed_at = login.updated_at = now
            login.idle_expires_at = min(
                login.expires_at, now + timedelta(seconds=security.settings.refresh_idle_seconds)
            )
            result = issue_result(security, user, login, now)
            session.add(
                RefreshToken(
                    owner_id=owner_id,
                    session_id=session_id,
                    parent_id=token.id,
                    created_at=now,
                    expires_at=login.idle_expires_at,
                    token_hash=refresh_digest(result.refresh_value),
                )
            )
    if result is None:
        raise AuthError()
    return result


def current_account(factory: sessionmaker[Session], identity: AccessIdentity) -> AccountDetail:
    with factory() as session:
        # 一条语句检查用户和会话，避免跨查询读取不一致状态。
        user = session.scalar(
            select(User)
            .join(SessionToken, SessionToken.owner_id == User.id)
            .where(
                User.id == identity.owner_id,
                SessionToken.id == identity.session_id,
                User.disabled_at.is_(None),
                SessionToken.revoked_at.is_(None),
                SessionToken.expires_at > func.clock_timestamp(),
                SessionToken.idle_expires_at > func.clock_timestamp(),
            )
        )
        if user is None:
            raise AuthError()
        return account_detail(user)


def logout_session(
    factory: sessionmaker[Session], identity: AccessIdentity | None, value: str | None
) -> None:
    with transaction(factory) as session:
        token_id = None
        if identity is None:
            owner_id, session_id, token_id = refresh_lookup(session, value)
        else:
            owner_id, session_id = identity.owner_id, identity.session_id
        _, login, now = locked_session(session, owner_id, session_id)
        if token_id is not None:
            token = session.scalar(
                select(RefreshToken).where(RefreshToken.id == token_id).with_for_update()
            )
            if token is None or token.consumed_at is not None or token.expires_at <= now:
                raise AuthError()
        login.revoked_at, login.revoked_reason, login.updated_at = now, "logout", now
