"""记录、思考脉络及发布的接口模型；不注册业务路由。"""

from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, model_validator

ContentType = Literal["knowledge", "experience", "memory_note", "thought"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EditorNode(ApiModel):
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
    attrs: dict[str, JsonValue] = Field(default_factory=dict)
    marks: list[dict[str, JsonValue]] = Field(default_factory=list)
    content: list["EditorNode"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_node(self) -> Self:
        if self.type == "text" and (self.text is None or self.content):
            raise ValueError("文本节点需要 text 且不能包含子节点")
        if self.type != "text" and self.text is not None:
            raise ValueError("仅文本节点允许 text")
        if self.type in {"image", "file", "htmlEmbed"}:
            attachment_id = self.attrs.get("attachment_id")
            if not isinstance(attachment_id, str):
                raise ValueError("文件节点需要 attachment_id")
            UUID(attachment_id)
        if self.type == "externalEmbed":
            url = self.attrs.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                raise ValueError("外部嵌入需要 HTTP(S) 链接")
        return self

    def has_text(self) -> bool:
        return bool(self.type == "text" and self.text and self.text.strip()) or any(
            child.has_text() for child in self.content
        )


class Document(ApiModel):
    type: Literal["doc"] = "doc"
    content: list[EditorNode] = Field(default_factory=list)

    def has_text(self) -> bool:
        return any(node.has_text() for node in self.content)


class ContentCreate(ApiModel):
    request_id: UUID
    title: str = ""
    body: Document = Field(default_factory=Document)
    content_type: ContentType | None = None
    space_id: UUID | None = None
    category_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)
    attachment_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_location(self) -> Self:
        if self.category_id is not None and self.space_id is None:
            raise ValueError("选择分类时必须同时提供空间")
        if len(set(self.tag_ids)) != len(self.tag_ids):
            raise ValueError("tag_ids 不能重复")
        if len(set(self.attachment_ids)) != len(self.attachment_ids):
            raise ValueError("attachment_ids 不能重复")
        if not self.body.has_text() and not self.attachment_ids:
            raise ValueError("记录需要文字或附件")
        return self


class ContentPatch(ApiModel):
    expected_version: int = Field(ge=1)
    title: str = ""
    body: Document = Field(default_factory=Document)
    content_type: ContentType | None = None
    space_id: UUID | None = None
    category_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)
    attachment_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        changed = self.model_fields_set - {"expected_version"}
        if not changed:
            raise ValueError("至少提供一个修改字段")
        for field in ("title", "body", "tag_ids", "attachment_ids"):
            if field in changed and getattr(self, field) is None:
                raise ValueError(f"{field} 不允许为 null")
        if self.tag_ids is not None and len(set(self.tag_ids)) != len(self.tag_ids):
            raise ValueError("tag_ids 不能重复")
        if len(set(self.attachment_ids)) != len(self.attachment_ids):
            raise ValueError("attachment_ids 不能重复")
        if (
            {"body", "attachment_ids"} <= changed
            and not self.body.has_text()
            and not self.attachment_ids
        ):
            raise ValueError("记录需要文字或附件")
        return self


class ContentSummary(ApiModel):
    id: UUID
    title: str
    content_type: ContentType | None
    space_id: UUID | None
    category_id: UUID | None
    display_name: str
    version: int = Field(ge=1)
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ContentDetail(ContentSummary):
    body: Document
    tag_ids: list[UUID]
    attachment_ids: list[UUID]


class ContentPage(ApiModel):
    items: list[ContentSummary]
    next_cursor: str | None


class ThreadCreate(ApiModel):
    request_id: UUID
    name: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_name(self) -> Self:
        if not self.name.strip():
            raise ValueError("主题名称不能为空")
        return self


class ThreadPatch(ApiModel):
    expected_version: int = Field(ge=1)
    name: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_name(self) -> Self:
        if not self.name.strip():
            raise ValueError("主题名称不能为空")
        return self


class VersionRequest(ApiModel):
    expected_version: int = Field(ge=1)


class ThreadDetail(ApiModel):
    id: UUID
    name: str
    version: int = Field(ge=1)
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ThreadPage(ApiModel):
    items: list[ThreadDetail]
    next_cursor: str | None


class ThreadTimelineItem(ApiModel):
    content: ContentSummary
    original_occurred_at: AwareDatetime | None
    imported_at: AwareDatetime | None


class ThreadTimeline(ApiModel):
    items: list[ThreadTimelineItem]
    next_cursor: str | None


class PublicationPreviewRequest(ApiModel):
    expected_version: int = Field(ge=1)
    public_attachment_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_attachments(self) -> Self:
        if len(set(self.public_attachment_ids)) != len(self.public_attachment_ids):
            raise ValueError("public_attachment_ids 不能重复")
        return self


class PublicationRequest(PublicationPreviewRequest):
    request_id: UUID
    expected_publication_version: int = Field(ge=0)


class PublicationPreview(ApiModel):
    content_id: UUID
    content_version: int = Field(ge=1)
    publication_version: int = Field(ge=0)
    title: str
    body: Document
    public_attachment_ids: list[UUID]


class PublicationDetail(ApiModel):
    content_id: UUID
    status: Literal["draft", "published", "withdrawn"]
    published_content_version: int | None
    publication_version: int = Field(ge=0)
    has_unpublished_changes: bool
    public_url: str | None
    published_at: AwareDatetime | None
    updated_at: AwareDatetime | None


class WithdrawRequest(ApiModel):
    expected_publication_version: int = Field(ge=1)
