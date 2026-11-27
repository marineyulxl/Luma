from datetime import datetime
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Space(Base):
    __tablename__ = "spaces"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("owner_id", "name_key"),
        {"comment": "知识空间表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="空间ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, comment="名称")
    name_key: Mapped[str] = mapped_column(Text, nullable=False, comment="规范化名称")
    description: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="", comment="简介"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="排序值"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("owner_id", "space_id", "id"),
        ForeignKeyConstraint(
            ["owner_id", "space_id"], ["spaces.owner_id", "spaces.id"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["owner_id", "space_id", "parent_id"],
            ["categories.owner_id", "categories.space_id", "categories.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_self"),
        {"comment": "目录分类表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="分类ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    space_id: Mapped[UUID] = mapped_column(nullable=False, comment="空间ID")
    parent_id: Mapped[UUID | None] = mapped_column(nullable=True, comment="上级分类ID")
    name: Mapped[str] = mapped_column(Text, nullable=False, comment="名称")
    name_key: Mapped[str] = mapped_column(Text, nullable=False, comment="规范化名称")
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="排序值"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("owner_id", "id"),
        UniqueConstraint("owner_id", "name_key"),
        {"comment": "标签表"},
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, nullable=False, comment="标签ID"
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, comment="名称")
    name_key: Mapped[str] = mapped_column(Text, nullable=False, comment="规范化名称")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间"
    )


class ContentTag(Base):
    __tablename__ = "content_tags"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "content_id"], ["contents.owner_id", "contents.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["owner_id", "tag_id"], ["tags.owner_id", "tags.id"], ondelete="CASCADE"
        ),
        {"comment": "记录与标签关联表"},
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="所有者ID"
    )
    content_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False, comment="记录ID")
    tag_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False, comment="标签ID")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


Index(
    "uq_categories_root",
    Category.owner_id,
    Category.space_id,
    Category.name_key,
    unique=True,
    postgresql_where=Category.parent_id.is_(None),
)
Index(
    "uq_categories_child",
    Category.owner_id,
    Category.space_id,
    Category.parent_id,
    Category.name_key,
    unique=True,
    postgresql_where=Category.parent_id.is_not(None),
)
Index("ix_content_tags_owner_id_content_id", ContentTag.owner_id, ContentTag.content_id)
Index("ix_content_tags_owner_id_tag_id", ContentTag.owner_id, ContentTag.tag_id)
