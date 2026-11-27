"""模型注册入口；迁移和测试从这里加载完整 metadata。"""

from app.db.base import Base
from app.modules.accounts.models import RefreshToken, SessionToken, User
from app.modules.attachments.models import Attachment, ContentAttachment
from app.modules.content.models import (
    Content,
    ContentBody,
    ContentRelation,
    ContentSource,
    IndexJob,
)
from app.modules.ingestion.models import (
    Conversation,
    ConversationMessage,
    ImportItem,
    ImportJob,
    IngestionRun,
    NormalizedDocument,
    RawAsset,
    Source,
    SourceVersion,
)
from app.modules.organization.models import Category, ContentTag, Space, Tag

__all__ = [
    "Base",
    "User",
    "SessionToken",
    "RefreshToken",
    "Space",
    "Category",
    "Tag",
    "ContentTag",
    "Content",
    "ContentBody",
    "ContentRelation",
    "ContentSource",
    "IndexJob",
    "Attachment",
    "ContentAttachment",
    "Source",
    "SourceVersion",
    "RawAsset",
    "ImportJob",
    "ImportItem",
    "Conversation",
    "ConversationMessage",
    "IngestionRun",
    "NormalizedDocument",
]
