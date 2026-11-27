"""Separate login sessions from rotating refresh token history.

Revision ID: 9c3d8a1f6b20
Revises: 782568a18b39
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c3d8a1f6b20"
down_revision: str | Sequence[str] | None = "782568a18b39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=True, comment="刷新空闲到期时间"),
    )
    op.add_column(
        "sessions",
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True, comment="最近刷新时间"),
    )
    op.add_column(
        "sessions", sa.Column("revoked_reason", sa.Text(), nullable=True, comment="撤销原因")
    )
    # Existing credentials never become valid refresh tokens. Normalize legacy
    # timestamps before installing constraints, including already-expired rows.
    op.execute("""
        UPDATE sessions
        SET expires_at = GREATEST(expires_at, created_at + INTERVAL '1 microsecond'),
            idle_expires_at = GREATEST(expires_at, created_at + INTERVAL '1 microsecond'),
            last_refreshed_at = created_at,
            revoked_at = GREATEST(COALESCE(revoked_at, clock_timestamp()), created_at),
            revoked_reason = 'legacy_upgrade',
            updated_at = GREATEST(clock_timestamp(), created_at)
    """)
    for name in ("idle_expires_at", "last_refreshed_at"):
        op.alter_column("sessions", name, existing_type=sa.DateTime(timezone=True), nullable=False)
    op.alter_column("sessions", "expires_at", existing_type=sa.DateTime(timezone=True), comment="绝对到期时间")
    op.alter_column("sessions", "created_at", existing_type=sa.DateTime(timezone=True), comment="登录时间")
    op.drop_constraint(op.f("uq_sessions_token_hash"), "sessions", type_="unique")
    op.drop_column("sessions", "token_hash")
    op.create_check_constraint(op.f("ck_sessions_absolute_expiry"), "sessions", "expires_at > created_at")
    op.create_check_constraint(
        op.f("ck_sessions_idle_expiry"), "sessions",
        "last_refreshed_at >= created_at AND idle_expires_at > last_refreshed_at "
        "AND idle_expires_at <= expires_at",
    )
    op.create_check_constraint(
        op.f("ck_sessions_revocation_state"), "sessions",
        "(revoked_at IS NULL AND revoked_reason IS NULL) OR "
        "(revoked_at IS NOT NULL AND revoked_reason IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_sessions_revocation_time"), "sessions",
        "revoked_at IS NULL OR revoked_at >= created_at",
    )
    op.create_check_constraint(
        op.f("ck_sessions_revocation_reason"), "sessions",
        "revoked_reason IS NULL OR revoked_reason IN "
        "('logout','password_changed','refresh_reuse','account_disabled','admin','legacy_upgrade')",
    )
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_index(
        "ix_sessions_idle_expires_at", "sessions", ["idle_expires_at"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False, comment="刷新令牌ID"),
        sa.Column("owner_id", sa.Uuid(), nullable=False, comment="所有者ID"),
        sa.Column("session_id", sa.Uuid(), nullable=False, comment="会话ID"),
        sa.Column("parent_id", sa.Uuid(), nullable=True, comment="前一令牌ID"),
        sa.Column("token_hash", sa.Text(), nullable=False, comment="令牌哈希"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"), comment="签发时间",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, comment="令牌到期时间"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True, comment="使用时间"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("owner_id", "id", name=op.f("uq_refresh_tokens_owner_id_id")),
        sa.UniqueConstraint(
            "owner_id", "session_id", "id", name=op.f("uq_refresh_tokens_owner_id_session_id_id")
        ),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
        sa.UniqueConstraint("parent_id", name=op.f("uq_refresh_tokens_parent_id")),
        sa.ForeignKeyConstraint(
            ["owner_id", "session_id"], ["sessions.owner_id", "sessions.id"],
            name=op.f("fk_refresh_tokens_owner_id_session_id_sessions"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "session_id", "parent_id"],
            ["refresh_tokens.owner_id", "refresh_tokens.session_id", "refresh_tokens.id"],
            name=op.f("fk_refresh_tokens_owner_id_session_id_parent_id_refresh_tokens"),
            ondelete="NO ACTION",
        ),
        sa.CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_refresh_tokens_hash_format")),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name=op.f("ck_refresh_tokens_not_self_parent")),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_refresh_tokens_expiry")),
        sa.CheckConstraint("consumed_at IS NULL OR consumed_at >= created_at", name=op.f("ck_refresh_tokens_consumed_time")),
        comment="刷新令牌表",
    )
    op.create_index("ix_refresh_tokens_session_id_id", "refresh_tokens", ["session_id", "id"])
    op.create_index(
        "uq_refresh_tokens_session_root", "refresh_tokens", ["session_id"], unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "uq_refresh_tokens_session_unconsumed", "refresh_tokens", ["session_id"], unique=True,
        postgresql_where=sa.text("consumed_at IS NULL"),
    )


def downgrade() -> None:
    # Downgrading invalidates all sessions. Old credentials are deliberately
    # unrecoverable, and the placeholder cannot authenticate an active session.
    op.execute("""
        UPDATE sessions
        SET revoked_at = GREATEST(COALESCE(revoked_at, clock_timestamp()), created_at),
            revoked_reason = COALESCE(revoked_reason, 'admin'),
            updated_at = GREATEST(clock_timestamp(), created_at)
    """)
    op.drop_table("refresh_tokens")
    op.add_column(
        "sessions", sa.Column("token_hash", sa.Text(), nullable=True, comment="会话令牌哈希")
    )
    op.execute("""
        UPDATE sessions
        SET token_hash = 'revoked:' || id::text || ':' || gen_random_uuid()::text
    """)
    op.alter_column("sessions", "token_hash", existing_type=sa.Text(), nullable=False)
    op.create_unique_constraint(op.f("uq_sessions_token_hash"), "sessions", ["token_hash"])
    op.drop_index("ix_sessions_idle_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    for name in (
        "revocation_reason", "revocation_time", "revocation_state", "idle_expiry", "absolute_expiry"
    ):
        op.drop_constraint(op.f(f"ck_sessions_{name}"), "sessions", type_="check")
    for name in ("revoked_reason", "last_refreshed_at", "idle_expires_at"):
        op.drop_column("sessions", name)
    op.alter_column("sessions", "expires_at", existing_type=sa.DateTime(timezone=True), comment="过期时间")
    op.alter_column("sessions", "created_at", existing_type=sa.DateTime(timezone=True), comment="创建时间")
