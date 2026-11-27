"""补充 V1.0 业务的 OpenAPI 定义；仅描述接口，不注册路由。"""

import re
from typing import Any

from pydantic import BaseModel

from app.api import business_schemas


def query(name: str, kind: str = "string", required: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": kind}
    if name.endswith("_id"):
        schema["format"] = "uuid"
    if name == "expected_version":
        schema["minimum"] = 1
    if name.endswith("_at") or name.endswith("_after") or name.endswith("_before"):
        schema["format"] = "date-time"
    return {"name": name, "in": "query", "required": required, "schema": schema}


def extend_business_contract(contract: dict[str, Any]) -> None:
    schemas = contract["components"]["schemas"]
    for value in vars(business_schemas).values():
        if (
            isinstance(value, type)
            and issubclass(value, BaseModel)
            and value.__module__ == business_schemas.__name__
            and value.__name__ != "Page"
            and value.__name__.isidentifier()
        ):
            schema = value.model_json_schema(ref_template="#/components/schemas/{model}")
            schemas.update(schema.pop("$defs", {}))
            schemas[value.__name__] = schema

    def add(
        method: str,
        path: str,
        operation_id: str,
        tag: str,
        summary: str,
        output: str | None,
        request: str | None = None,
        *,
        status: int = 200,
        public: bool = False,
        parameters: list[dict[str, Any]] | None = None,
        binary: bool = False,
    ) -> dict[str, Any]:
        responses: dict[str, Any] = {
            str(code): {
                "description": message,
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            }
            for code, message in (
                (404, "资源不存在或对调用者不可见"),
                (409, "版本冲突、状态冲突或幂等载荷不同"),
                (422, "输入不符合契约"),
                (429, "请求过于频繁"),
                (500, "服务处理失败"),
            )
        }
        if not public:
            responses["401"] = {
                "description": "未登录或会话过期",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            }
        if output is None:
            responses[str(status)] = {"description": "成功，无响应体"}
        else:
            media = "application/octet-stream" if binary else "application/json"
            schema = (
                {"type": "string", "format": "binary"}
                if binary
                else {"$ref": f"#/components/schemas/{output}"}
            )
            responses[str(status)] = {
                "description": "已接收，按任务详情查询结果" if status == 202 else "操作成功",
                "content": {media: {"schema": schema}},
            }
            if status in {201, 202}:
                responses["200"] = {
                    "description": "同一 request_id 与载荷的幂等重试",
                    "content": {media: {"schema": schema}},
                }
                responses[str(status)]["headers"] = {
                    "Location": {"schema": {"type": "string"}, "description": "资源或任务地址"}
                }
        operation: dict[str, Any] = {
            "tags": [tag],
            "operationId": operation_id,
            "summary": summary,
            "x-implementation-status": "planned",
            "x-authentication-required": not public,
            "responses": responses,
        }
        path_parameters = [
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": {
                    "type": "string",
                    **({"format": "uuid"} if name.endswith("_id") else {}),
                },
            }
            for name in re.findall(r"\{([^}]+)\}", path)
        ]
        if path_parameters or parameters:
            operation["parameters"] = path_parameters + (parameters or [])
        if request:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {"schema": {"$ref": f"#/components/schemas/{request}"}}
                },
            }
        contract["paths"].setdefault(path, {})[method] = operation
        return operation

    page = [
        {
            "name": "limit",
            "in": "query",
            "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30},
        },
        query("cursor"),
    ]
    updated = [query("expected_updated_at", required=True)]
    version = [query("expected_version", "integer", True)]

    add(
        "post",
        "/api/auth/sessions",
        "sessions_create",
        "accounts",
        "登录所有者账号",
        "SessionDetail",
        "LoginRequest",
        public=True,
    )
    add(
        "post",
        "/api/auth/sessions/refresh",
        "sessions_refresh",
        "accounts",
        "轮换刷新凭据并签发新访问令牌",
        "SessionDetail",
        public=True,
    )
    add(
        "delete",
        "/api/auth/sessions/current",
        "sessions_delete",
        "accounts",
        "退出并使当前会话失效",
        None,
        status=204,
    )
    add("get", "/api/account", "account_detail", "accounts", "当前所有者资料", "AccountDetail")
    add(
        "patch",
        "/api/account",
        "account_update",
        "accounts",
        "修改显示名称",
        "AccountDetail",
        "AccountPatch",
    )
    add(
        "put",
        "/api/account/password",
        "account_password_update",
        "accounts",
        "修改密码并撤销所有会话",
        None,
        "PasswordChange",
        status=204,
    )

    add(
        "get",
        "/api/spaces",
        "spaces_list",
        "organization",
        "空间列表",
        "SpacePage",
        parameters=page,
    )
    add(
        "post",
        "/api/spaces",
        "spaces_create",
        "organization",
        "新建空间",
        "SpaceDetail",
        "SpaceCreate",
        status=201,
    )
    add("get", "/api/spaces/{space_id}", "spaces_detail", "organization", "空间详情", "SpaceDetail")
    add(
        "patch",
        "/api/spaces/{space_id}",
        "spaces_update",
        "organization",
        "修改空间名称和说明",
        "SpaceDetail",
        "SpacePatch",
    )
    add(
        "delete",
        "/api/spaces/{space_id}",
        "spaces_delete",
        "organization",
        "删除空空间",
        None,
        status=204,
        parameters=updated,
    )
    add(
        "put",
        "/api/spaces/order",
        "spaces_reorder",
        "organization",
        "调整完整空间顺序",
        None,
        "OrderRequest",
        status=204,
    )
    add(
        "get",
        "/api/spaces/{space_id}/categories",
        "categories_list",
        "organization",
        "平铺分页获取分类并按 parent_id 组树",
        "CategoryPage",
        parameters=page,
    )
    add(
        "post",
        "/api/spaces/{space_id}/categories",
        "categories_create",
        "organization",
        "新建分类",
        "CategoryDetail",
        "CategoryCreate",
        status=201,
    )
    add(
        "get",
        "/api/categories/{category_id}",
        "categories_detail",
        "organization",
        "分类详情",
        "CategoryDetail",
    )
    add(
        "patch",
        "/api/categories/{category_id}",
        "categories_update",
        "organization",
        "重命名或在同空间移动分类",
        "CategoryDetail",
        "CategoryPatch",
    )
    add(
        "delete",
        "/api/categories/{category_id}",
        "categories_delete",
        "organization",
        "删除空分类",
        None,
        status=204,
        parameters=updated,
    )
    add(
        "get",
        "/api/tags",
        "tags_list",
        "organization",
        "标签列表或名称搜索",
        "TagPage",
        parameters=page + [query("q")],
    )
    add(
        "post",
        "/api/tags",
        "tags_create",
        "organization",
        "创建标签",
        "TagDetail",
        "NamedCreate",
        status=201,
    )
    add(
        "patch",
        "/api/tags/{tag_id}",
        "tags_update",
        "organization",
        "重命名标签",
        "TagDetail",
        "TagPatch",
    )
    add(
        "delete",
        "/api/tags/{tag_id}",
        "tags_delete",
        "organization",
        "删除标签并保留记录",
        None,
        status=204,
        parameters=updated,
    )
    add(
        "get",
        "/api/content-types",
        "content_types_list",
        "organization",
        "读取固定内容类型",
        "ContentTypeOptions",
    )

    add(
        "delete",
        "/api/contents/{content_id}",
        "contents_delete",
        "trash",
        "移入回收站并停止公开",
        None,
        status=204,
        parameters=version,
    )
    add(
        "get",
        "/api/trash",
        "trash_list",
        "trash",
        "按删除时间倒序浏览回收站",
        "TrashPage",
        parameters=page,
    )
    add(
        "get",
        "/api/trash/{content_id}",
        "trash_detail",
        "trash",
        "所有者查看待恢复原文",
        "ContentDetail",
    )
    add(
        "post",
        "/api/trash/{content_id}/restore",
        "trash_restore",
        "trash",
        "恢复记录并保持私有",
        "ContentRestoreResult",
        "VersionRequest",
    )
    add(
        "delete",
        "/api/trash/{content_id}",
        "trash_purge",
        "trash",
        "永久删除回收站中的记录",
        None,
        status=204,
        parameters=version,
    )

    upload = add(
        "post",
        "/api/attachments",
        "attachments_upload",
        "attachments",
        "上传一个文件并校验完整性",
        "AttachmentDetail",
        status=201,
    )
    upload["requestBody"] = {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["request_id", "file"],
                    "properties": {
                        "request_id": {"type": "string", "format": "uuid"},
                        "file": {"type": "string", "format": "binary"},
                    },
                }
            }
        },
    }
    for code, description in ((413, "文件超过上限"), (415, "文件格式不支持")):
        upload["responses"][str(code)] = {
            "description": description,
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
            },
        }
    add(
        "get",
        "/api/attachments/{attachment_id}",
        "attachments_detail",
        "attachments",
        "读取附件状态",
        "AttachmentDetail",
    )
    add(
        "delete",
        "/api/attachments/{attachment_id}",
        "attachments_delete",
        "attachments",
        "删除没有任何引用的附件",
        None,
        status=204,
    )
    add(
        "get",
        "/api/attachments/{attachment_id}/download",
        "attachments_download",
        "attachments",
        "鉴权下载原文件",
        "binary",
        binary=True,
    )
    add(
        "get",
        "/api/attachments/{attachment_id}/embed",
        "attachments_embed",
        "attachments",
        "获取隔离 HTML 展示信息",
        "EmbedView",
    )
    add(
        "get",
        "/api/contents/{content_id}/attachments",
        "content_attachments_list",
        "attachments",
        "记录附件列表",
        "AttachmentPage",
        parameters=page,
    )

    add("get", "/api/sources", "sources_list", "sources", "来源列表", "SourcePage", parameters=page)
    add(
        "delete",
        "/api/sources/{source_id}",
        "sources_delete",
        "sources",
        "清理无记录引用的来源及原件",
        None,
        status=204,
    )
    add(
        "get",
        "/api/sources/{source_id}",
        "sources_detail",
        "sources",
        "来源身份详情",
        "SourceDetail",
    )
    add(
        "get",
        "/api/sources/{source_id}/versions",
        "source_versions_list",
        "sources",
        "来源版本列表",
        "SourceVersionPage",
        parameters=page,
    )
    add(
        "get",
        "/api/source-versions/{source_version_id}",
        "source_versions_detail",
        "sources",
        "来源版本及原件引用",
        "SourceVersionDetail",
    )
    add(
        "get",
        "/api/contents/{content_id}/sources",
        "content_sources_list",
        "sources",
        "记录的来源证据",
        "ContentSourcePage",
        parameters=page,
    )
    add(
        "post",
        "/api/contents/{content_id}/sources",
        "content_sources_create",
        "sources",
        "关联已有来源版本",
        "ContentSourceDetail",
        "ContentSourceCreate",
        status=201,
    )
    add(
        "delete",
        "/api/contents/{content_id}/sources/{content_source_id}",
        "content_sources_delete",
        "sources",
        "解除来源引用并保留原件",
        None,
        status=204,
        parameters=version,
    )
    add(
        "get",
        "/api/contents/{content_id}/relations",
        "relations_list",
        "relations",
        "关联和反向引用",
        "RelationPage",
        parameters=page
        + [
            {
                "name": "direction",
                "in": "query",
                "schema": {
                    "type": "string",
                    "enum": ["all", "incoming", "outgoing"],
                    "default": "all",
                },
            }
        ],
    )
    add(
        "post",
        "/api/contents/{content_id}/relations",
        "relations_create",
        "relations",
        "创建记录关系",
        "RelationDetail",
        "RelationCreate",
        status=201,
    )
    add(
        "delete",
        "/api/relations/{relation_id}",
        "relations_delete",
        "relations",
        "删除双端关系引用",
        None,
        status=204,
    )
    add(
        "get",
        "/api/search",
        "search_contents",
        "search",
        "私人标题正文搜索及摘要",
        "SearchPage",
        parameters=page
        + [query("q", required=True), query("space_id"), query("category_id"), query("tag_id")],
    )

    add(
        "post",
        "/api/import-previews",
        "import_previews_create",
        "imports",
        "解析待导入资料供选择",
        "ImportPreviewDetail",
        "ImportPreviewRequest",
        status=202,
    )
    add(
        "get",
        "/api/import-previews/{preview_id}",
        "import_previews_detail",
        "imports",
        "查询预览处理状态",
        "ImportPreviewDetail",
    )
    add(
        "get",
        "/api/import-previews/{preview_id}/items",
        "import_candidates_list",
        "imports",
        "分页预览会话或文件候选",
        "ImportCandidatePage",
        parameters=page,
    )
    add(
        "post",
        "/api/imports",
        "imports_create",
        "imports",
        "确认选择后提交导入批次",
        "ImportJobDetail",
        "ImportCreate",
        status=202,
    )
    add(
        "get",
        "/api/imports",
        "imports_list",
        "imports",
        "导入批次列表",
        "ImportJobPage",
        parameters=page,
    )
    add(
        "get",
        "/api/imports/{job_id}",
        "imports_detail",
        "imports",
        "批次统计和状态",
        "ImportJobDetail",
    )
    add(
        "get",
        "/api/imports/{job_id}/items",
        "import_items_list",
        "imports",
        "导入单项状态和错误",
        "ImportItemPage",
        parameters=page,
    )
    add(
        "post",
        "/api/imports/{job_id}/retries",
        "imports_retry",
        "imports",
        "仅重试指定失败或部分成功项目",
        "ImportJobDetail",
        "RetryImportRequest",
        status=202,
    )
    add(
        "post",
        "/api/reparses",
        "reparses_create",
        "imports",
        "从原件产生新版候选解析",
        "ProcessingDetail",
        "ReparseRequest",
        status=202,
    )
    add(
        "get",
        "/api/reparses/{run_id}",
        "reparses_detail",
        "imports",
        "查询重解析结果",
        "ProcessingDetail",
    )
    add(
        "get",
        "/api/normalized-documents/{document_id}",
        "normalized_documents_detail",
        "imports",
        "读取待确认规范正文",
        "NormalizedDocumentDetail",
    )
    add(
        "post",
        "/api/contents/{content_id}/parsed-updates",
        "parsed_updates_apply",
        "imports",
        "确认后应用指定解析结果",
        "ContentDetail",
        "ApplyParsedRequest",
    )
    add(
        "get",
        "/api/source-versions/{source_version_id}/conversation",
        "conversations_detail",
        "imports",
        "读取原始会话信息",
        "ConversationDetail",
    )
    add(
        "get",
        "/api/conversations/{conversation_id}/messages",
        "conversation_messages_list",
        "imports",
        "按顺序读取原始消息和分支信息",
        "ConversationMessagePage",
        parameters=page,
    )

    add(
        "post",
        "/api/exports",
        "exports_create",
        "data",
        "单条或批量 Markdown 导出",
        "JobDetail",
        "ExportCreate",
        status=202,
    )
    add(
        "get",
        "/api/exports/{job_id}",
        "exports_detail",
        "data",
        "查询导出状态及转换警告",
        "JobDetail",
    )
    add(
        "get",
        "/api/exports/{job_id}/download",
        "exports_download",
        "data",
        "下载成功的导出文件",
        "binary",
        binary=True,
    )
    add(
        "post",
        "/api/backups",
        "backups_create",
        "data",
        "创建完整一致性备份",
        "JobDetail",
        "RequestIdentity",
        status=202,
    )
    add("get", "/api/backups", "backups_list", "data", "备份任务列表", "JobPage", parameters=page)
    add("get", "/api/backups/{job_id}", "backups_detail", "data", "查询备份状态", "JobDetail")
    add(
        "get",
        "/api/backups/{job_id}/download",
        "backups_download",
        "data",
        "下载完整备份",
        "binary",
        binary=True,
    )
    add(
        "post",
        "/api/backup-inspections",
        "backup_inspections_create",
        "data",
        "检查上传备份并预览恢复清单",
        "BackupInspection",
        "BackupInspectionRequest",
    )
    add(
        "post",
        "/api/restores",
        "restores_create",
        "data",
        "确认后恢复至空白工作区",
        "JobDetail",
        "RestoreCreate",
        status=202,
    )
    add("get", "/api/restores/{job_id}", "restores_detail", "data", "查询恢复结果", "JobDetail")

    add(
        "get",
        "/api/public/site",
        "public_site_detail",
        "public",
        "Site 基本公开信息",
        "PublicSiteDetail",
        public=True,
    )
    add(
        "get",
        "/api/public/contents",
        "public_contents_list",
        "public",
        "公开首页列表与公开搜索",
        "PublicContentPage",
        public=True,
        parameters=page + [query("q"), query("category_key"), query("tag_key")],
    )
    add(
        "get",
        "/api/public/contents/{slug}",
        "public_contents_detail",
        "public",
        "上次成功发布的内容版本",
        "PublicContentDetail",
        public=True,
    )
    add(
        "get",
        "/api/public/categories",
        "public_categories_list",
        "public",
        "仅包含公开记录的分类",
        "PublicLinkPage",
        public=True,
        parameters=page,
    )
    add(
        "get",
        "/api/public/tags",
        "public_tags_list",
        "public",
        "仅包含公开记录的标签",
        "PublicLinkPage",
        public=True,
        parameters=page,
    )
    add(
        "get",
        "/api/public/contents/{slug}/attachments/{attachment_key}",
        "public_attachments_download",
        "public",
        "校验当前发布范围后返回附件",
        "binary",
        public=True,
        binary=True,
    )
    add(
        "get",
        "/api/public/contents/{slug}/embeds/{attachment_key}",
        "public_attachments_embed",
        "public",
        "校验发布范围后获取隔离 HTML 展示",
        "EmbedView",
        public=True,
    )
    add(
        "get",
        "/api/public/sitemap",
        "public_sitemap_list",
        "public",
        "公开站点地图数据",
        "SitemapPage",
        public=True,
        parameters=page,
    )

    filters = [
        {
            "name": "content_type",
            "in": "query",
            "schema": {
                "type": "string",
                "enum": ["knowledge", "experience", "memory_note", "thought"],
            },
        },
        query("updated_after"),
        query("updated_before"),
        query("unclassified", "boolean"),
        {
            "name": "sort",
            "in": "query",
            "schema": {
                "type": "string",
                "enum": ["updated_desc", "relevance"],
                "default": "updated_desc",
            },
        },
    ]
    contract["paths"]["/api/contents"]["get"]["parameters"].extend(filters)
    contract["paths"]["/api/search"]["get"]["parameters"].extend(filters)
