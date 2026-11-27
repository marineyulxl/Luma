from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Content(Base):
    __tablename__ = "contents"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("owner_id", "create_request_id"),
        ForeignKeyConstraint(
            ["owner_id", "space_id"], ["spaces.owner_id", "spaces.id"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["owner_id", "space_id", "category_id"],
            ["categories.owner_id", "categories.space_id", "categories.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint("lifecycle_status IN ('active','archived')", name="lifecycle"),
        CheckConstraint("category_id IS NULL OR space_id IS NOT NULL", name="category_space"),
        CheckConstraint(
            "content_type IS NULL OR content_type IN ('knowledge','experience','memory_note','thought')",
            name="content_type",
        ),
        CheckConstraint(
            "learning_state IS NULL OR learning_state IN ('to_learn','learning','understood','applied')",
            name="learning",
        ),
        {"comment": "记录主表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="记录ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    create_request_id: Mapped[UUID] = mapped_column(nullable=False, comment="新建请求ID")
    create_request_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="新建请求摘要")
    title: Mapped[str] = mapped_column(Text, nullable=False, server_default="", comment="标题")
    content_type: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内容类型")
    space_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="空间ID")
    category_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="分类ID")
    learning_state: Mapped[str | None] = mapped_column(Text, nullable=True, comment="学习状态")
    lifecycle_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="active", comment="生命周期状态"
    )
    version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="1", comment="并发版本号"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="删除时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class ContentBody(Base):
    __tablename__ = "content_bodies"
    __table_args__ = (
        UniqueConstraint("owner_id", "content_id"),
        ForeignKeyConstraint(
            ["owner_id", "content_id"], ["contents.owner_id", "contents.id"], ondelete="CASCADE"
        ),
        CheckConstraint(
            "jsonb_typeof(body_json) = 'object' AND COALESCE(body_json->>'type', '') = 'doc'",
            name="document",
        ),
        CheckConstraint("schema_version > 0", name="schema_version"),
        {"comment": "记录正文表"},
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    content_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False, comment="记录ID")
    body_json: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, nullable=False, comment="结构化正文"
    )
    plain_text: Mapped[str] = mapped_column(Text, nullable=False, comment="正文纯文本")
    schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1", comment="正文结构版本"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class ContentRelation(Base):
    __tablename__ = "content_relations"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("owner_id", "from_content_id", "to_content_id", "relation_type"),
        ForeignKeyConstraint(
            ["owner_id", "from_content_id"],
            ["contents.owner_id", "contents.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["owner_id", "to_content_id"], ["contents.owner_id", "contents.id"], ondelete="CASCADE"
        ),
        CheckConstraint("from_content_id <> to_content_id", name="not_self"),
        CheckConstraint(
            "relation_type IN ('related_to','prerequisite','application','contrast')", name="type"
        ),
        CheckConstraint(
            "relation_type <> 'related_to' OR from_content_id < to_content_id", name="canonical"
        ),
        {"comment": "记录关系表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="关系ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    from_content_id: Mapped[UUID] = mapped_column(nullable=False, comment="关系起点记录")
    to_content_id: Mapped[UUID] = mapped_column(nullable=False, comment="关系终点记录")
    relation_type: Mapped[str] = mapped_column(Text, nullable=False, comment="关系类型")
    note: Mapped[str] = mapped_column(Text, nullable=False, server_default="", comment="关系说明")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class ContentSource(Base):
    __tablename__ = "content_sources"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        ForeignKeyConstraint(
            ["owner_id", "content_id"], ["contents.owner_id", "contents.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["owner_id", "source_version_id"],
            ["source_versions.owner_id", "source_versions.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["owner_id", "source_version_id", "normalized_document_id"],
            [
                "normalized_documents.owner_id",
                "normalized_documents.source_version_id",
                "normalized_documents.id",
            ],
            ondelete="RESTRICT",
        ),
        {"comment": "记录来源引用表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="来源引用ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    content_id: Mapped[UUID] = mapped_column(nullable=False, comment="记录ID")
    source_version_id: Mapped[UUID] = mapped_column(nullable=False, comment="来源版本ID")
    normalized_document_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="解析结果ID")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class IndexJob(Base):
    __tablename__ = "index_jobs"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("content_id", "content_version", "index_kind", "processor_version"),
        ForeignKeyConstraint(
            ["owner_id", "content_id"], ["contents.owner_id", "contents.id"], ondelete="CASCADE"
        ),
        CheckConstraint(
            "status IN ('queued','processing','success','failed','cancelled')", name="status"
        ),
        CheckConstraint(
            "(status = 'processing') = (lease_token IS NOT NULL AND lease_until IS NOT NULL) AND ((lease_token IS NULL) = (lease_until IS NULL))",
            name="lease",
        ),
        CheckConstraint("content_version > 0 AND attempt_count >= 0", name="version_attempt"),
        CheckConstraint("index_kind = 'search'", name="kind"),
        {"comment": "索引任务表"},
    )

    content_id: Mapped[UUID] = mapped_column(nullable=False, comment="记录ID")
    content_version: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="记录版本")
    index_kind: Mapped[str] = mapped_column(Text, nullable=False, comment="索引类型")
    processor_version: Mapped[str] = mapped_column(Text, nullable=False, comment="处理器版本")
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="queued", comment="任务状态"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="尝试次数"
    )
    lease_token: Mapped[UUID | None] = mapped_column(nullable=True, comment="租约标识")
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="租约到期时间"
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误说明")
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="索引任务表ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


Index(
    "ix_contents_recent",
    Content.owner_id,
    Content.updated_at.desc(),
    Content.id.desc(),
    postgresql_where=Content.deleted_at.is_(None),
)
Index(
    "ix_contents_trash",
    Content.owner_id,
    Content.deleted_at.desc(),
    Content.id.desc(),
    postgresql_where=Content.deleted_at.is_not(None),
)
Index(
    "ix_contents_location",
    Content.owner_id,
    Content.space_id,
    Content.category_id,
    Content.updated_at.desc(),
    Content.id.desc(),
    postgresql_where=Content.deleted_at.is_(None),
)
Index(
    "uq_content_sources_raw",
    ContentSource.content_id,
    ContentSource.source_version_id,
    unique=True,
    postgresql_where=ContentSource.normalized_document_id.is_(None),
)
Index(
    "uq_content_sources_parsed",
    ContentSource.content_id,
    ContentSource.source_version_id,
    ContentSource.normalized_document_id,
    unique=True,
    postgresql_where=ContentSource.normalized_document_id.is_not(None),
)
Index(
    "ix_content_relations_owner_id_to_content_id",
    ContentRelation.owner_id,
    ContentRelation.to_content_id,
)
Index("ix_index_jobs_owner_id_content_id", IndexJob.owner_id, IndexJob.content_id)
Index("ix_content_sources_owner_id_content_id", ContentSource.owner_id, ContentSource.content_id)
Index(
    "ix_content_sources_owner_id_source_version_id",
    ContentSource.owner_id,
    ContentSource.source_version_id,
)
Index(
    "ix_content_sources_owner_id_source_version_id_norm_188a75c079",
    ContentSource.owner_id,
    ContentSource.source_version_id,
    ContentSource.normalized_document_id,
)
Index("ix_index_jobs_claim", IndexJob.status, IndexJob.lease_until)
