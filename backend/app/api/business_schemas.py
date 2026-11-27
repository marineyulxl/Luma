"""V1.0 其余业务的接口数据模型；不创建路由或数据库连接。"""

from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, HttpUrl, SecretStr, model_validator

from app.modules.accounts.schemas import NewPassword
from app.modules.content.schemas import ApiModel, ContentDetail, ContentSummary, Document


class Page[T](ApiModel):
    items: list[T]
    next_cursor: str | None


class AccountDetail(ApiModel):
    id: UUID
    username: str
    display_name: str


class LoginRequest(ApiModel):
    username: str = Field(min_length=1, max_length=1024)
    password: SecretStr = Field(max_length=128)


class SessionDetail(ApiModel):
    account: AccountDetail
    expires_at: AwareDatetime
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    access_expires_in: int = Field(gt=0)


class AccountPatch(ApiModel):
    display_name: str = Field(min_length=1)


class PasswordChange(ApiModel):
    current_password: SecretStr
    new_password: NewPassword


class NamedCreate(ApiModel):
    request_id: UUID
    name: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_name(self) -> Self:
        if not self.name.strip():
            raise ValueError("名称不能为空")
        return self


class SpaceCreate(NamedCreate):
    description: str = ""


class NamedPatch(ApiModel):
    name: str = ""
    expected_updated_at: AwareDatetime

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        if not self.model_fields_set - {"expected_updated_at"}:
            raise ValueError("至少提供一个修改字段")
        if "name" in self.model_fields_set and not self.name.strip():
            raise ValueError("名称不能为空")
        return self


class SpacePatch(NamedPatch):
    description: str = ""


class SpaceDetail(ApiModel):
    id: UUID
    name: str
    description: str
    sort_order: int
    content_count: int = Field(ge=0)
    category_count: int = Field(ge=0)
    updated_at: AwareDatetime


class SpacePage(Page[SpaceDetail]):
    pass


class OrderRequest(ApiModel):
    ordered_ids: list[UUID]
    expected_order: list[UUID]

    @model_validator(mode="after")
    def validate_unique(self) -> Self:
        if len(set(self.ordered_ids)) != len(self.ordered_ids) or len(
            set(self.expected_order)
        ) != len(self.expected_order):
            raise ValueError("排序列表不能重复")
        if set(self.ordered_ids) != set(self.expected_order):
            raise ValueError("排序只能调整同一集合，不能增加或移除空间")
        return self


class CategoryCreate(NamedCreate):
    parent_id: UUID | None = None


class CategoryPatch(NamedPatch):
    parent_id: UUID | None = None
    sort_order: int = 0


class CategoryDetail(ApiModel):
    id: UUID
    space_id: UUID
    parent_id: UUID | None
    name: str
    sort_order: int
    updated_at: AwareDatetime


class CategoryPage(Page[CategoryDetail]):
    pass


class TagPatch(NamedPatch):
    pass


class TagDetail(ApiModel):
    id: UUID
    name: str
    updated_at: AwareDatetime


class TagPage(Page[TagDetail]):
    pass


class ContentTypeOption(ApiModel):
    value: Literal["knowledge", "experience", "memory_note", "thought"]
    label_key: str


class ContentTypeOptions(ApiModel):
    items: list[ContentTypeOption]


class TrashItem(ApiModel):
    content: ContentSummary
    deleted_at: AwareDatetime


class TrashPage(Page[TrashItem]):
    pass


class AttachmentDetail(ApiModel):
    id: UUID
    original_name: str
    mime_type: str
    byte_size: int = Field(ge=0)
    sha256: str | None
    status: Literal["pending", "ready", "failed"]
    created_at: AwareDatetime


class AttachmentPage(Page[AttachmentDetail]):
    pass


class EmbedView(ApiModel):
    url: HttpUrl
    sandbox: str
    expires_at: AwareDatetime
    fallback_url: HttpUrl


class SourceDetail(ApiModel):
    id: UUID
    kind: Literal["manual", "file", "url", "chatgpt", "other"]
    platform: str | None
    external_id: str | None
    external_url: str | None
    created_at: AwareDatetime


class SourcePage(Page[SourceDetail]):
    pass


class SourceVersionDetail(ApiModel):
    id: UUID
    source_id: UUID
    revision: int = Field(ge=1)
    original_created_at: AwareDatetime | None
    original_updated_at: AwareDatetime | None
    captured_at: AwareDatetime
    raw_attachment_ids: list[UUID]


class SourceVersionPage(Page[SourceVersionDetail]):
    pass


class ContentSourceCreate(ApiModel):
    request_id: UUID
    source_version_id: UUID
    normalized_document_id: UUID | None = None
    expected_version: int = Field(ge=1)


class ContentSourceDetail(ApiModel):
    id: UUID
    content_id: UUID
    source_version_id: UUID
    normalized_document_id: UUID | None
    content_version: int = Field(ge=1)


class ContentSourcePage(Page[ContentSourceDetail]):
    pass


class RelationCreate(ApiModel):
    request_id: UUID
    target_content_id: UUID
    relation_type: Literal["related_to", "prerequisite", "application", "contrast"]
    description: str = ""


class RelationDetail(ApiModel):
    id: UUID
    from_content_id: UUID
    to_content_id: UUID
    relation_type: Literal["related_to", "prerequisite", "application", "contrast"]
    description: str
    other: ContentSummary
    direction: Literal["incoming", "outgoing", "bidirectional"]


class RelationPage(Page[RelationDetail]):
    pass


class ImportPreviewRequest(ApiModel):
    request_id: UUID
    kind: Literal["files", "url", "chatgpt"]
    attachment_ids: list[UUID] = Field(default_factory=list)
    url: HttpUrl | None = None
    personal_summary: str = ""

    @model_validator(mode="after")
    def validate_input(self) -> Self:
        if self.kind == "url":
            if self.url is None or self.attachment_ids:
                raise ValueError("网页导入需要 URL，且不能同时提交文件")
        elif not self.attachment_ids or self.url is not None:
            raise ValueError("文件导入需要 attachment_ids，且不能同时提交 URL")
        if len(set(self.attachment_ids)) != len(self.attachment_ids):
            raise ValueError("attachment_ids 不能重复")
        return self


class ImportCandidate(ApiModel):
    item_key: str
    title: str
    preview_text: str
    message_count: int | None
    warnings: list[str]
    duplicate_content_id: UUID | None


class ImportPreviewDetail(ApiModel):
    id: UUID
    status: Literal["queued", "processing", "ready", "failed"]
    version: int = Field(ge=1)
    error_code: str | None
    expires_at: AwareDatetime


class ImportCandidatePage(Page[ImportCandidate]):
    pass


class ImportCreate(ApiModel):
    request_id: UUID
    preview_id: UUID
    preview_version: int = Field(ge=1)
    selected_item_keys: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        if len(set(self.selected_item_keys)) != len(self.selected_item_keys):
            raise ValueError("导入项目不能重复")
        return self


class ImportJobDetail(ApiModel):
    id: UUID
    status: Literal["queued", "processing", "success", "partial", "failed"]
    total: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ImportJobPage(Page[ImportJobDetail]):
    pass


class ImportItemDetail(ApiModel):
    id: UUID
    job_id: UUID
    source_version_id: UUID
    item_key: str
    status: Literal["queued", "processing", "success", "partial", "failed", "skipped"]
    content_id: UUID | None
    error_code: str | None
    error_detail: str | None
    normalized_document_id: UUID | None


class ImportItemPage(Page[ImportItemDetail]):
    pass


class RetryImportRequest(ApiModel):
    request_id: UUID
    item_ids: list[UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique(self) -> Self:
        if len(set(self.item_ids)) != len(self.item_ids):
            raise ValueError("重试项目不能重复")
        return self


class ReparseRequest(ApiModel):
    request_id: UUID
    source_version_id: UUID


class ProcessingDetail(ApiModel):
    id: UUID
    source_version_id: UUID
    status: Literal["queued", "processing", "success", "partial", "failed"]
    normalized_document_id: UUID | None
    error_code: str | None
    warnings: list[str]


class NormalizedDocumentDetail(ApiModel):
    id: UUID
    source_version_id: UUID
    body: Document
    plain_text: str
    warnings: list[str]


class ApplyParsedRequest(ApiModel):
    request_id: UUID
    normalized_document_id: UUID
    expected_version: int = Field(ge=1)


class ConversationDetail(ApiModel):
    id: UUID
    source_version_id: UUID
    platform: str
    external_id: str | None
    title: str
    occurred_at: AwareDatetime | None


class ConversationMessage(ApiModel):
    id: UUID
    sequence: int = Field(ge=0)
    external_message_id: str | None
    parent_external_id: str | None
    role: str
    text: str
    attachment_ids: list[UUID]
    occurred_at: AwareDatetime | None


class ConversationMessagePage(Page[ConversationMessage]):
    pass


class ExportCreate(ApiModel):
    request_id: UUID
    content_ids: list[UUID] = Field(min_length=1)
    include_metadata: bool = True

    @model_validator(mode="after")
    def validate_unique(self) -> Self:
        if len(set(self.content_ids)) != len(self.content_ids):
            raise ValueError("导出记录不能重复")
        return self


class JobDetail(ApiModel):
    id: UUID
    kind: Literal["markdown_export", "backup", "restore"]
    status: Literal["queued", "processing", "success", "failed"]
    error_code: str | None
    error_detail: str | None
    warnings: list[str]
    created_at: AwareDatetime
    updated_at: AwareDatetime


class JobPage(Page[JobDetail]):
    pass


class RequestIdentity(ApiModel):
    request_id: UUID


class BackupInspectionRequest(ApiModel):
    attachment_id: UUID


class BackupInspection(ApiModel):
    id: UUID
    attachment_id: UUID
    format_version: str
    checksum: str
    content_count: int = Field(ge=0)
    attachment_count: int = Field(ge=0)
    thread_count: int = Field(ge=0)
    compatible: bool
    workspace_empty: bool
    warnings: list[str]
    expires_at: AwareDatetime


class RestoreCreate(ApiModel):
    request_id: UUID
    inspection_id: UUID
    expected_checksum: str


class PublicContentSummary(ApiModel):
    slug: str
    title: str
    excerpt: str
    published_at: AwareDatetime
    updated_at: AwareDatetime


class PublicContentPage(Page[PublicContentSummary]):
    pass


class PublicLink(ApiModel):
    name: str
    key: str


class PublicLinkPage(Page[PublicLink]):
    pass


class PublicRelation(ApiModel):
    title: str
    slug: str
    relation_type: str


class PublicNodeAttributes(ApiModel):
    attachment_key: str | None = None
    url: str | None = None
    level: int | None = None
    language: str | None = None
    start: int | None = None
    colspan: int | None = None
    rowspan: int | None = None
    colwidth: list[int] | None = None
    align: str | None = None
    alt: str | None = None
    title: str | None = None
    href: str | None = None


class PublicMark(ApiModel):
    type: Literal["bold", "italic", "strike", "code", "link", "underline"]
    attrs: PublicNodeAttributes = Field(default_factory=PublicNodeAttributes)


class PublicEditorNode(ApiModel):
    type: Literal[
        "paragraph",
        "heading",
        "text",
        "bulletList",
        "orderedList",
        "listItem",
        "blockquote",
        "codeBlock",
        "hardBreak",
        "horizontalRule",
        "table",
        "tableRow",
        "tableCell",
        "tableHeader",
        "image",
        "file",
        "htmlEmbed",
        "externalEmbed",
    ]
    text: str | None = None
    attrs: PublicNodeAttributes = Field(default_factory=PublicNodeAttributes)
    marks: list[PublicMark] = Field(default_factory=list)
    content: list["PublicEditorNode"] = Field(default_factory=list)


class PublicDocument(ApiModel):
    type: Literal["doc"] = "doc"
    content: list[PublicEditorNode]


class PublicContentDetail(PublicContentSummary):
    body: PublicDocument
    relations: list[PublicRelation]
    attachment_keys: list[str]
    tags: list[PublicLink]
    category: PublicLink | None


class SitemapEntry(ApiModel):
    path: str
    last_modified_at: AwareDatetime


class SitemapPage(Page[SitemapEntry]):
    pass


class PublicSiteDetail(ApiModel):
    display_name: str
    content_base_path: Literal["/knowledge"] = "/knowledge"


class SearchHit(ApiModel):
    content: ContentSummary
    snippet: str
    matched_fields: list[Literal["title", "body"]]


class SearchPage(Page[SearchHit]):
    pass


class ContentRestoreResult(ApiModel):
    content: ContentDetail
    location_changed: bool
    publication_status: Literal["draft", "withdrawn"]
