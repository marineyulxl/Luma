from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("storage_key"),
        CheckConstraint("byte_size >= 0", name="size"),
        CheckConstraint("status IN ('pending','ready','failed')", name="status"),
        CheckConstraint("status <> 'ready' OR sha256 IS NOT NULL", name="ready_hash"),
        {"comment": "附件元数据表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="附件ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, comment="文件存储键")
    original_name: Mapped[str] = mapped_column(Text, nullable=False, comment="原始文件名")
    mime_type: Mapped[str] = mapped_column(Text, nullable=False, comment="文件媒体类型")
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件字节数")
    sha256: Mapped[str | None] = mapped_column(Text, nullable=True, comment="文件校验摘要")
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="pending", comment="文件状态"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class ContentAttachment(Base):
    __tablename__ = "content_attachments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "content_id"], ["contents.owner_id", "contents.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["owner_id", "attachment_id"],
            ["attachments.owner_id", "attachments.id"],
            ondelete="CASCADE",
        ),
        {"comment": "记录与附件关联表"},
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    content_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False, comment="记录ID")
    attachment_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False, comment="附件ID")
    role: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False, comment="附件用途")


Index("ix_content_attachments_owner_id", ContentAttachment.owner_id)
Index(
    "ix_content_attachments_owner_id_attachment_id",
    ContentAttachment.owner_id,
    ContentAttachment.attachment_id,
)
Index(
    "ix_content_attachments_owner_id_content_id",
    ContentAttachment.owner_id,
    ContentAttachment.content_id,
)
