from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        CheckConstraint("privacy_scope = 'private'", name="privacy"),
        {"comment": "来源身份表"},
    )

    kind: Mapped[str] = mapped_column(Text, nullable=False, comment="来源类型")
    platform: Mapped[str | None] = mapped_column(Text, nullable=True, comment="来源平台")
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True, comment="外部ID")
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="来源链接")
    privacy_scope: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="private", comment="使用权限"
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="来源身份表ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


class SourceVersion(Base):
    __tablename__ = "source_versions"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("source_id", "revision"),
        ForeignKeyConstraint(
            ["owner_id", "source_id"], ["sources.owner_id", "sources.id"], ondelete="RESTRICT"
        ),
        CheckConstraint("revision > 0", name="revision"),
        {"comment": "来源版本表"},
    )

    source_id: Mapped[UUID] = mapped_column(nullable=False, comment="来源ID")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, comment="来源版本号")
    checksum: Mapped[str] = mapped_column(Text, nullable=False, comment="原文摘要")
    original_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="原始创建时间"
    )
    original_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="原始更新时间"
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="采集时间"
    )
    metadata_json: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"), comment="来源元数据"
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="来源版本表ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


class RawAsset(Base):
    __tablename__ = "raw_assets"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        ForeignKeyConstraint(
            ["owner_id", "source_version_id"],
            ["source_versions.owner_id", "source_versions.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["owner_id", "attachment_id"],
            ["attachments.owner_id", "attachments.id"],
            ondelete="RESTRICT",
        ),
        {"comment": "原始资料表"},
    )

    source_version_id: Mapped[UUID] = mapped_column(nullable=False, comment="来源版本ID")
    attachment_id: Mapped[UUID] = mapped_column(nullable=False, comment="存储附件ID")
    asset_role: Mapped[str] = mapped_column(Text, nullable=False, comment="资料角色")
    metadata_json: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"), comment="资料元数据"
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="原始资料表ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("owner_id", "idempotency_key"),
        CheckConstraint(
            "status IN ('queued','processing','success','partial','failed','skipped')",
            name="status",
        ),
        {"comment": "导入批次表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="导入批次ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False, comment="导入类型")
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="queued", comment="批次状态"
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, comment="幂等标识")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class ImportItem(Base):
    __tablename__ = "import_items"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("job_id", "item_key"),
        UniqueConstraint("owner_id", "source_version_id", "id"),
        ForeignKeyConstraint(
            ["owner_id", "job_id"], ["import_jobs.owner_id", "import_jobs.id"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["owner_id", "source_version_id"],
            ["source_versions.owner_id", "source_versions.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["owner_id", "content_id"], ["contents.owner_id", "contents.id"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["owner_id", "raw_attachment_id"],
            ["attachments.owner_id", "attachments.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('queued','processing','success','partial','failed','skipped')",
            name="status",
        ),
        {"comment": "导入单项表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="导入项ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    job_id: Mapped[UUID] = mapped_column(nullable=False, comment="导入批次ID")
    source_version_id: Mapped[UUID] = mapped_column(nullable=False, comment="来源版本ID")
    item_key: Mapped[str] = mapped_column(Text, nullable=False, comment="批次内项目标识")
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="queued", comment="导入状态"
    )
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误代码")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误说明")
    content_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="记录ID")
    source_hash: Mapped[str | None] = mapped_column(Text, nullable=True, comment="来源内容摘要")
    raw_attachment_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="原文件附件ID")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("import_item_id"),
        ForeignKeyConstraint(
            ["owner_id", "source_version_id", "import_item_id"],
            ["import_items.owner_id", "import_items.source_version_id", "import_items.id"],
            ondelete="RESTRICT",
        ),
        {"comment": "原始对话表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="对话ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    import_item_id: Mapped[UUID] = mapped_column(nullable=False, comment="导入项ID")
    platform: Mapped[str] = mapped_column(Text, nullable=False, comment="来源平台")
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True, comment="外部ID")
    title: Mapped[str] = mapped_column(Text, nullable=False, comment="标题")
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="原始发生时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )
    source_version_id: Mapped[UUID] = mapped_column(nullable=False, comment="来源版本ID")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("conversation_id", "sequence"),
        ForeignKeyConstraint(
            ["owner_id", "conversation_id"],
            ["conversations.owner_id", "conversations.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("sequence >= 0", name="sequence"),
        {"comment": "原始对话消息表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="消息ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, comment="原始对话ID")
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, comment="消息顺序")
    external_message_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="平台消息ID"
    )
    parent_external_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="平台上级消息ID"
    )
    role: Mapped[str] = mapped_column(Text, nullable=False, comment="消息角色")
    body: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, nullable=False, comment="原始消息内容"
    )
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="原始发生时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("import_item_id", "attempt"),
        UniqueConstraint("owner_id", "source_version_id", "id"),
        ForeignKeyConstraint(
            ["owner_id", "source_version_id", "import_item_id"],
            ["import_items.owner_id", "import_items.source_version_id", "import_items.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('queued','processing','success','partial','failed','needs_review','cancelled')",
            name="status",
        ),
        CheckConstraint(
            "(status = 'processing') = (lease_token IS NOT NULL AND lease_until IS NOT NULL) AND ((lease_token IS NULL) = (lease_until IS NULL))",
            name="lease",
        ),
        CheckConstraint("attempt > 0", name="attempt"),
        CheckConstraint(
            "stage IN ('normalize','clean','materialize','index_dispatch')", name="stage"
        ),
        {"comment": "采集处理记录表"},
    )

    import_item_id: Mapped[UUID] = mapped_column(nullable=False, comment="导入项ID")
    source_version_id: Mapped[UUID] = mapped_column(nullable=False, comment="来源版本ID")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, comment="尝试序号")
    parser_name: Mapped[str] = mapped_column(Text, nullable=False, comment="解析器名称")
    parser_version: Mapped[str] = mapped_column(Text, nullable=False, comment="解析器版本")
    config_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="配置摘要")
    stage: Mapped[str] = mapped_column(Text, nullable=False, comment="处理阶段")
    status: Mapped[str] = mapped_column(Text, nullable=False, comment="执行状态")
    lease_token: Mapped[UUID | None] = mapped_column(nullable=True, comment="租约标识")
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="租约到期时间"
    )
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误代码")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误说明")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="结束时间"
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="采集处理记录表ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


class NormalizedDocument(Base):
    __tablename__ = "normalized_documents"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("owner_id", "source_version_id", "id"),
        ForeignKeyConstraint(
            ["owner_id", "source_version_id", "ingestion_run_id"],
            ["ingestion_runs.owner_id", "ingestion_runs.source_version_id", "ingestion_runs.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("schema_version > 0", name="schema_version"),
        CheckConstraint("jsonb_typeof(warnings) = 'array'", name="warnings"),
        {"comment": "规范解析结果表"},
    )

    ingestion_run_id: Mapped[UUID] = mapped_column(nullable=False, comment="处理记录ID")
    source_version_id: Mapped[UUID] = mapped_column(nullable=False, comment="来源版本ID")
    canonical_format: Mapped[str] = mapped_column(Text, nullable=False, comment="规范格式")
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, comment="结构版本")
    body: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, nullable=False, comment="规范内容"
    )
    plain_text: Mapped[str] = mapped_column(Text, nullable=False, comment="解析纯文本")
    content_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="解析内容摘要")
    warnings: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="解析警告"
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="规范解析结果表ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


Index("ix_source_versions_owner_id_source_id", SourceVersion.owner_id, SourceVersion.source_id)
Index("ix_raw_assets_owner_id_attachment_id", RawAsset.owner_id, RawAsset.attachment_id)
Index("ix_raw_assets_owner_id_source_version_id", RawAsset.owner_id, RawAsset.source_version_id)
Index("ix_import_items_owner_id_content_id", ImportItem.owner_id, ImportItem.content_id)
Index("ix_import_items_owner_id_job_id", ImportItem.owner_id, ImportItem.job_id)
Index(
    "ix_import_items_owner_id_raw_attachment_id", ImportItem.owner_id, ImportItem.raw_attachment_id
)
Index(
    "ix_conversations_owner_id_source_version_id_import_item_id",
    Conversation.owner_id,
    Conversation.source_version_id,
    Conversation.import_item_id,
)
Index(
    "ix_ingestion_runs_owner_id_source_version_id_import_item_id",
    IngestionRun.owner_id,
    IngestionRun.source_version_id,
    IngestionRun.import_item_id,
)
Index(
    "ix_conversation_messages_owner_id_conversation_id",
    ConversationMessage.owner_id,
    ConversationMessage.conversation_id,
)
Index(
    "ix_normalized_documents_owner_id_source_version_id_bca6b8becf",
    NormalizedDocument.owner_id,
    NormalizedDocument.source_version_id,
    NormalizedDocument.ingestion_run_id,
)
Index("ix_ingestion_runs_claim", IngestionRun.status, IngestionRun.lease_until)
Index(
    "ix_ingestion_runs_item",
    IngestionRun.owner_id,
    IngestionRun.import_item_id,
    IngestionRun.attempt,
)
Index(
    "ix_normalized_documents_run", NormalizedDocument.owner_id, NormalizedDocument.ingestion_run_id
)
