"""生成 V1.0 业务接口契约；运行路由由应用单独注册。"""

from typing import Any

from pydantic import BaseModel

from app.api.business_contract import extend_business_contract
from app.api.schemas import ErrorResponse
from app.modules.content.schemas import (
    ContentCreate,
    ContentDetail,
    ContentPage,
    ContentPatch,
    PublicationDetail,
    PublicationPreview,
    PublicationPreviewRequest,
    PublicationRequest,
    ThreadCreate,
    ThreadDetail,
    ThreadPage,
    ThreadPatch,
    ThreadTimeline,
    VersionRequest,
    WithdrawRequest,
)


def reference(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def response(name: str, description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": reference(name)}},
    }


def record_contract() -> dict[str, Any]:
    models: tuple[type[BaseModel], ...] = (
        ContentCreate,
        ContentPatch,
        ContentDetail,
        ContentPage,
        ErrorResponse,
        ThreadCreate,
        ThreadPatch,
        ThreadDetail,
        ThreadPage,
        ThreadTimeline,
        VersionRequest,
        PublicationRequest,
        PublicationPreview,
        PublicationPreviewRequest,
        PublicationDetail,
        WithdrawRequest,
    )
    schemas: dict[str, Any] = {}
    for model in models:
        schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        schemas.update(schema.pop("$defs", {}))
        schemas[model.__name__] = schema
    errors = {
        str(code): response("ErrorResponse", description)
        for code, description in (
            (401, "未登录或会话失效"),
            (422, "参数校验失败"),
            (500, "服务处理失败"),
        )
    }
    conflict = response("ErrorResponse", "版本冲突、幂等载荷不同或引用状态冲突")
    not_found = response("ErrorResponse", "记录不存在、已删除或不属于当前用户")
    operation = {
        "tags": ["contents"],
        "x-implementation-status": "planned",
        "x-authentication-required": True,
    }

    def body(name: str) -> dict[str, Any]:
        return {"required": True, "content": {"application/json": {"schema": reference(name)}}}

    path_id = {
        "name": "content_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "format": "uuid"},
    }
    parameters = [
        {
            "name": "limit",
            "in": "query",
            "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30},
        },
        {
            "name": "cursor",
            "in": "query",
            "schema": {"type": "string"},
            "description": "不透明游标，绑定当前筛选条件",
        },
    ]
    for name in ("space_id", "category_id", "tag_id"):
        parameters.append(
            {"name": name, "in": "query", "schema": {"type": "string", "format": "uuid"}}
        )
    parameters.append(
        {
            "name": "q",
            "in": "query",
            "schema": {"type": "string"},
            "description": "按标题和正文纯文本搜索，排除已删除记录",
        }
    )
    contract: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "Luma V1.0 API 契约",
            "version": "0.3.0",
            "description": "设计契约，尚未注册业务路由。会话传输方式及输入上限待确定，不可据此视为可调用 API。",
        },
        "x-status": "draft",
        "x-pending-decisions": ["会话传输方式与过期策略", "正文及请求大小限制"],
        "paths": {
            "/api/contents": {
                "post": {
                    **operation,
                    "operationId": "contents_create",
                    "summary": "新建记录",
                    "requestBody": body("ContentCreate"),
                    "responses": {
                        **errors,
                        "201": {
                            **response("ContentDetail", "首次创建"),
                            "headers": {
                                "Location": {
                                    "schema": {"type": "string"},
                                    "description": "记录详情的相对地址",
                                }
                            },
                        },
                        "200": response("ContentDetail", "相同 request_id 和载荷的重试"),
                        "409": conflict,
                    },
                },
                "get": {
                    **operation,
                    "operationId": "contents_list",
                    "summary": "记录列表",
                    "parameters": parameters,
                    "responses": {
                        **errors,
                        "200": response("ContentPage", "按 updated_at、id 倒序，列表不含正文"),
                    },
                },
            },
            "/api/contents/{content_id}": {
                "parameters": [path_id],
                "get": {
                    **operation,
                    "operationId": "contents_detail",
                    "summary": "记录详情",
                    "responses": {
                        **errors,
                        "200": response("ContentDetail", "返回正文和当前版本"),
                        "404": not_found,
                    },
                },
                "patch": {
                    **operation,
                    "operationId": "contents_update",
                    "summary": "保存记录",
                    "requestBody": body("ContentPatch"),
                    "responses": {
                        **errors,
                        "200": response("ContentDetail", "保存后的新版本"),
                        "404": not_found,
                        "409": conflict,
                    },
                },
            },
        },
        "components": {"schemas": schemas},
    }

    def planned_operation(
        operation_id: str,
        summary: str,
        tag: str,
        output: str | None,
        request: str | None = None,
        created: bool = False,
    ) -> dict[str, Any]:
        responses = {**errors, "404": not_found, "409": conflict}
        if output is None:
            responses["204"] = {"description": "操作成功，无响应体"}
        else:
            responses["201" if created else "200"] = response(output, "操作成功")
            if created:
                responses["201"]["headers"] = {
                    "Location": {"schema": {"type": "string"}, "description": "新资源地址"}
                }
                responses["200"] = response(output, "相同 request_id 及载荷的重试")
        result: dict[str, Any] = {
            **operation,
            "tags": [tag],
            "operationId": operation_id,
            "summary": summary,
            "responses": responses,
        }
        if request:
            result["requestBody"] = body(request)
        return result

    def uuid_parameter(name: str) -> dict[str, Any]:
        return {
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": "string", "format": "uuid"},
        }

    page_parameters = parameters[:2]
    contract["paths"].update(
        {
            "/api/threads": {
                "get": {
                    **planned_operation(
                        "threads_list", "私人思考主题列表", "threads", "ThreadPage"
                    ),
                    "parameters": page_parameters,
                },
                "post": planned_operation(
                    "threads_create",
                    "创建私人思考主题",
                    "threads",
                    "ThreadDetail",
                    "ThreadCreate",
                    True,
                ),
            },
            "/api/threads/{thread_id}": {
                "parameters": [uuid_parameter("thread_id")],
                "get": planned_operation(
                    "threads_detail", "思考主题详情", "threads", "ThreadDetail"
                ),
                "patch": planned_operation(
                    "threads_update",
                    "修改主题名称",
                    "threads",
                    "ThreadDetail",
                    "ThreadPatch",
                ),
                "delete": {
                    **planned_operation(
                        "threads_delete", "删除主题并保留原始记录", "threads", None
                    ),
                    "parameters": [
                        {
                            "name": "expected_version",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "integer", "minimum": 1},
                        }
                    ],
                },
            },
            "/api/threads/{thread_id}/timeline": {
                "parameters": [uuid_parameter("thread_id")],
                "get": {
                    **planned_operation(
                        "threads_timeline",
                        "按记录创建时间升序回看，排除回收站记录",
                        "threads",
                        "ThreadTimeline",
                    ),
                    "parameters": page_parameters,
                },
            },
            "/api/threads/{thread_id}/members/{content_id}": {
                "parameters": [uuid_parameter("thread_id"), path_id],
                "put": planned_operation(
                    "threads_member_add",
                    "幂等加入记录并返回主题新版本",
                    "threads",
                    "ThreadDetail",
                    "VersionRequest",
                ),
                "delete": {
                    **planned_operation(
                        "threads_member_remove",
                        "幂等移出记录并保留原文",
                        "threads",
                        "ThreadDetail",
                    ),
                    "parameters": [
                        {
                            "name": "expected_version",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "integer", "minimum": 1},
                        }
                    ],
                },
            },
            "/api/contents/{content_id}/publication": {
                "parameters": [path_id],
                "get": planned_operation(
                    "publications_detail",
                    "查询发布状态及未发布修改",
                    "publications",
                    "PublicationDetail",
                ),
                "post": planned_operation(
                    "publications_publish",
                    "首次发布或更新公开版本",
                    "publications",
                    "PublicationDetail",
                    "PublicationRequest",
                ),
            },
            "/api/contents/{content_id}/publication/preview": {
                "parameters": [path_id],
                "post": planned_operation(
                    "publications_preview",
                    "预览指定已保存版本及选定附件",
                    "publications",
                    "PublicationPreview",
                    "PublicationPreviewRequest",
                ),
            },
            "/api/contents/{content_id}/publication/withdraw": {
                "parameters": [path_id],
                "post": planned_operation(
                    "publications_withdraw",
                    "撤回指定公开版本",
                    "publications",
                    "PublicationDetail",
                    "WithdrawRequest",
                ),
            },
        }
    )
    extend_business_contract(contract)
    contract["components"]["securitySchemes"] = {
        "accessToken": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        "refreshCookie": {"type": "apiKey", "in": "cookie", "name": "luma_refresh"},
    }
    stages = {
        "accounts": "M0",
        "organization": "Beta",
        "attachments": "Beta",
        "sources": "Beta",
        "imports": "Beta",
        "search": "Alpha/Beta",
        "contents": "Alpha/Beta",
        "trash": "Alpha/Release",
        "relations": "Release",
        "threads": "Release",
        "publications": "Release",
        "data": "Release",
        "public": "Release",
    }
    for path in contract["paths"].values():
        for method, item in path.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            item["x-delivery-stage"] = stages[item["tags"][0]]
            item["security"] = [{"accessToken": []}] if item["x-authentication-required"] else []
            if item["x-authentication-required"]:
                item["responses"].setdefault("401", response("ErrorResponse", "访问令牌失效"))
            if method in {"post", "patch", "put", "delete"}:
                item["responses"].setdefault("403", response("ErrorResponse", "请求来源校验失败"))
            item["responses"].setdefault("429", response("ErrorResponse", "请求过于频繁"))
    refresh = contract["paths"]["/api/auth/sessions/refresh"]["post"]
    refresh["x-authentication-required"] = True
    refresh["security"] = [{"refreshCookie": []}]
    refresh["responses"]["401"] = response("ErrorResponse", "刷新凭据失效、撤销或检测到重用")
    logout = contract["paths"]["/api/auth/sessions/current"]["delete"]
    logout["security"] = [{"accessToken": []}, {"refreshCookie": []}]
    for path in ("/api/auth/sessions", "/api/auth/sessions/refresh"):
        contract["paths"][path]["post"]["responses"]["200"]["headers"] = {
            "Set-Cookie": {
                "schema": {"type": "string"},
                "description": "写入轮换后的 HttpOnly 刷新 Cookie",
            },
            "Cache-Control": {"schema": {"type": "string", "const": "no-store"}},
        }
    logout["responses"]["204"]["headers"] = {
        "Set-Cookie": {"schema": {"type": "string"}, "description": "清除刷新 Cookie"}
    }
    contract["paths"]["/api/account/password"]["put"]["responses"]["204"]["headers"] = logout[
        "responses"
    ]["204"]["headers"]
    contract["info"]["description"] = (
        "V1.0 接口定义。登录、刷新、退出与当前用户接口已实现，其他操作按阶段交付。"
        "业务鉴权使用 JWT Bearer，刷新凭据使用 HttpOnly Cookie。"
    )
    contract["x-pending-decisions"] = ["请求与文件上限", "HTML 展示权限"]
    for path, method in (
        ("/api/auth/sessions", "post"),
        ("/api/auth/sessions/refresh", "post"),
        ("/api/auth/sessions/current", "delete"),
        ("/api/account", "get"),
    ):
        contract["paths"][path][method]["x-implementation-status"] = "implemented"
        if method == "post":
            contract["paths"][path][method]["parameters"] = [
                {"name": "Origin", "in": "header", "required": True, "schema": {"type": "string"}}
            ]
    logout["parameters"] = [
        {
            "name": "Origin",
            "in": "header",
            "required": False,
            "description": "使用刷新 Cookie 退出时必须提供允许的来源",
            "schema": {"type": "string"},
        }
    ]
    contract["paths"]["/api/auth/sessions"]["post"]["responses"]["401"] = response(
        "ErrorResponse", "账号或密码错误，统一提示，不泄露账号存在性"
    )
    return contract
