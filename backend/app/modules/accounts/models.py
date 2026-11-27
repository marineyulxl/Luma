from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = ({"comment": "用户表"},)

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="用户ID"
    )
    username: Mapped[str] = mapped_column(Text, nullable=False, comment="登录账号")
    password_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="密码哈希")
    display_name: Mapped[str] = mapped_column(Text, nullable=False, comment="显示名称")
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="停用时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class SessionToken(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        CheckConstraint("expires_at > created_at", name="absolute_expiry"),
        CheckConstraint(
            "last_refreshed_at >= created_at AND idle_expires_at > last_refreshed_at "
            "AND idle_expires_at <= expires_at",
            name="idle_expiry",
        ),
        CheckConstraint(
            "(revoked_at IS NULL AND revoked_reason IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoked_reason IS NOT NULL)",
            name="revocation_state",
        ),
        CheckConstraint("revoked_at IS NULL OR revoked_at >= created_at", name="revocation_time"),
        CheckConstraint(
            "revoked_reason IS NULL OR revoked_reason IN "
            "('logout','password_changed','refresh_reuse','account_disabled','admin','legacy_upgrade')",
            name="revocation_reason",
        ),
        {"comment": "登录会话表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="会话ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="绝对到期时间"
    )
    idle_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="刷新空闲到期时间"
    )
    last_refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="最近刷新时间"
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="撤销时间"
    )
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="撤销原因")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="登录时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("owner_id", "session_id", "id"),
        UniqueConstraint("token_hash"),
        UniqueConstraint("parent_id"),
        ForeignKeyConstraint(
            ["owner_id", "session_id"], ["sessions.owner_id", "sessions.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["owner_id", "session_id", "parent_id"],
            ["refresh_tokens.owner_id", "refresh_tokens.session_id", "refresh_tokens.id"],
            ondelete="NO ACTION",
        ),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="hash_format"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_self_parent"),
        CheckConstraint("expires_at > created_at", name="expiry"),
        CheckConstraint("consumed_at IS NULL OR consumed_at >= created_at", name="consumed_time"),
        Index("ix_refresh_tokens_session_id_id", "session_id", "id"),
        Index(
            "uq_refresh_tokens_session_root",
            "session_id",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
        Index(
            "uq_refresh_tokens_session_unconsumed",
            "session_id",
            unique=True,
            postgresql_where=text("consumed_at IS NULL"),
        ),
        {"comment": "刷新令牌表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="刷新令牌ID"
    )
    owner_id: Mapped[UUID] = mapped_column(nullable=False, comment="所有者ID")
    session_id: Mapped[UUID] = mapped_column(nullable=False, comment="会话ID")
    parent_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="前一令牌ID")
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="令牌哈希")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="签发时间"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="令牌到期时间"
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="使用时间"
    )


Index("ix_sessions_expires_at", SessionToken.expires_at)
Index(
    "ix_sessions_idle_expires_at",
    SessionToken.idle_expires_at,
    postgresql_where=SessionToken.revoked_at.is_(None),
)
Index("uq_users_username_lower", func.lower(User.username), unique=True)
