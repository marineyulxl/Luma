"""契约文件、请求 Schema 与待实现状态的一致性。"""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from openapi_spec_validator import validate
from pydantic import ValidationError

from app.api.contract import record_contract
from app.main import create_app
from app.modules.content.schemas import ContentCreate, ContentPatch


def test_implemented_contract_matches_registered_routes():
    runtime = create_app().openapi()
    for path, methods in record_contract()["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            if operation.get("x-implementation-status") != "implemented":
                continue
            actual = runtime["paths"][path][method]
            assert actual["operationId"] == operation["operationId"]
            assert actual.get("security", []) == operation["security"]
            if "requestBody" in operation:
                assert actual["requestBody"] == operation["requestBody"]
            for status in ("200", "204"):
                if status in operation["responses"]:
                    assert actual["responses"][status].get("content") == operation["responses"][
                        status
                    ].get("content")


def test_openapi_contract_valid_and_export_in_sync():
    contract = record_contract()
    validate(contract)
    path = Path(__file__).resolve().parents[2] / "docs/architecture/api/openapi.json"
    assert json.loads(path.read_text(encoding="utf-8")) == contract
    assert contract["x-status"] == "draft"
    operations = [
        operation
        for path in contract["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post", "patch", "put", "delete"}
    ]
    assert len(operations) == 93
    implemented = {"sessions_create", "sessions_refresh", "sessions_delete", "account_detail"}
    assert {
        op["operationId"] for op in operations if op["x-implementation-status"] == "implemented"
    } == implemented
    assert all(
        op["x-implementation-status"] == "planned"
        for op in operations
        if op["operationId"] not in implemented
    )
    assert len({op["operationId"] for op in operations}) == len(operations)
    for op in operations:
        expected_auth = op["tags"] != ["public"] and op["operationId"] != "sessions_create"
        assert op["x-authentication-required"] == expected_auth


def test_create_is_low_burden_but_rejects_owner_override():
    request_id = uuid4()
    record = ContentCreate(
        request_id=request_id,
        body={
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "记录"}]}],
        },
    )
    assert record.title == "" and record.body.type == "doc"
    with pytest.raises(ValidationError):
        ContentCreate(request_id=request_id, attachment_ids=[uuid4()], owner_id=uuid4())


@pytest.mark.parametrize("field", ["title", "body", "tag_ids", "attachment_ids"])
def test_patch_omitted_and_null_have_distinct_semantics(field):
    patch = ContentPatch(expected_version=1, title="new")
    assert "body" not in patch.model_fields_set
    with pytest.raises(ValidationError):
        ContentPatch.model_validate({"expected_version": 1, field: None})


def test_patch_requires_version_and_actual_change():
    with pytest.raises(ValidationError):
        ContentPatch.model_validate({"title": "new"})
    with pytest.raises(ValidationError):
        ContentPatch(expected_version=1)
    patch = ContentPatch(expected_version=1, content_type=None)
    assert patch.model_dump(exclude_unset=True) == {"expected_version": 1, "content_type": None}


def test_duplicate_tags_and_category_without_space_rejected():
    tag = uuid4()
    with pytest.raises(ValidationError):
        ContentCreate(request_id=uuid4(), tag_ids=[tag, tag])
    with pytest.raises(ValidationError):
        ContentCreate(request_id=uuid4(), category_id=uuid4())


@pytest.mark.parametrize("text", ["", " ", "\n\t"])
def test_empty_records_rejected_but_attachment_only_records_allowed(text):
    with pytest.raises(ValidationError):
        ContentCreate(
            request_id=uuid4(),
            body={
                "type": "doc",
                "content": [{"type": "text", "text": text}],
            },
        )
    record = ContentCreate(request_id=uuid4(), attachment_ids=[uuid4()])
    assert record.title == ""
    with pytest.raises(ValidationError):
        ContentPatch(expected_version=1, body={"type": "doc"}, attachment_ids=[])


@pytest.mark.parametrize(
    "field,value", [("learning_state", "learning"), ("lifecycle_status", "archived")]
)
def test_removed_features_cannot_be_submitted(field, value):
    with pytest.raises(ValidationError):
        ContentCreate.model_validate(
            {"request_id": uuid4(), "attachment_ids": [uuid4()], field: value}
        )
    with pytest.raises(ValidationError):
        ContentPatch.model_validate({"expected_version": 1, field: value})


def test_document_rejects_unknown_nodes_and_missing_attachment_reference():
    for node in [{"type": "script"}, {"type": "htmlEmbed"}, {"type": "text"}]:
        with pytest.raises(ValidationError):
            ContentCreate.model_validate(
                {
                    "request_id": uuid4(),
                    "attachment_ids": [uuid4()],
                    "body": {"type": "doc", "content": [node]},
                }
            )


def test_publication_contract_requires_previewed_version_and_attachment_selection():
    from app.modules.content.schemas import PublicationRequest

    with pytest.raises(ValidationError):
        PublicationRequest.model_validate({"request_id": uuid4()})
    contract = record_contract()
    record_parameters = contract["paths"]["/api/contents"]["get"]["parameters"]
    assert "lifecycle_status" not in {param["name"] for param in record_parameters}
    summary = contract["components"]["schemas"]["ContentSummary"]["properties"]
    assert "display_name" in summary
    assert not {"learning_state", "lifecycle_status"} & summary.keys()


def test_every_business_operation_has_a_documented_contract():
    contract = record_contract()
    document = (Path(__file__).resolve().parents[2] / "docs/architecture/API.md").read_text(
        encoding="utf-8"
    )
    for path, methods in contract["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            row = f"| {method.upper()} | {path} | {operation['operationId']} |"
            assert row in document
            assert operation["x-delivery-stage"]
    for capability in (
        "ACC",
        "STU",
        "INB",
        "CNT",
        "SPC",
        "TYP",
        "IMP",
        "SRC",
        "SEA",
        "REL",
        "THR",
        "PUB",
        "DAT",
        "APP",
    ):
        assert f"| {capability} " in document


def test_public_document_cannot_reuse_private_attachment_identifiers():
    from app.api.business_schemas import PublicContentDetail, PublicNodeAttributes

    with pytest.raises(ValidationError):
        PublicNodeAttributes.model_validate({"attachment_id": str(uuid4())})
    assert "owner_id" not in PublicContentDetail.model_fields
    assert "source_version_id" not in PublicContentDetail.model_fields
    public_operations = record_contract()["paths"]["/api/public/contents/{slug}"]
    assert public_operations["get"]["x-authentication-required"] is False
    assert "401" not in public_operations["get"]["responses"]


def test_import_requires_one_source_kind_and_unique_selection():
    from app.api.business_schemas import ImportCreate, ImportPreviewRequest, RetryImportRequest

    with pytest.raises(ValidationError):
        ImportPreviewRequest(request_id=uuid4(), kind="files")
    with pytest.raises(ValidationError):
        ImportPreviewRequest(
            request_id=uuid4(),
            kind="url",
            url="http://example.com",
            attachment_ids=[uuid4()],
        )
    with pytest.raises(ValidationError):
        ImportCreate(
            request_id=uuid4(),
            preview_id=uuid4(),
            preview_version=1,
            selected_item_keys=["same", "same"],
        )
    item = uuid4()
    with pytest.raises(ValidationError):
        RetryImportRequest(request_id=uuid4(), item_ids=[item, item])


def test_upload_and_async_jobs_have_transport_specific_responses():
    contract = record_contract()
    upload = contract["paths"]["/api/attachments"]["post"]
    assert "multipart/form-data" in upload["requestBody"]["content"]
    assert {"413", "415"} <= upload["responses"].keys()
    for path in ("/api/imports", "/api/exports", "/api/backups", "/api/restores"):
        operation = contract["paths"][path]["post"]
        assert "202" in operation["responses"]
        assert "Location" in operation["responses"]["202"]["headers"]


def test_organization_patch_preserves_omitted_values_and_allows_explicit_root():
    from datetime import UTC, datetime

    from app.api.business_schemas import CategoryPatch, SpacePatch, TagPatch

    stamp = datetime.now(UTC)
    patch = SpacePatch(expected_updated_at=stamp, description="changed")
    assert patch.model_dump(exclude_unset=True) == {
        "expected_updated_at": stamp,
        "description": "changed",
    }
    category = CategoryPatch(expected_updated_at=stamp, parent_id=None)
    assert category.model_dump(exclude_unset=True)["parent_id"] is None
    assert "name" not in category.model_fields_set
    with pytest.raises(ValidationError):
        SpacePatch(expected_updated_at=stamp)
    with pytest.raises(ValidationError):
        TagPatch(expected_updated_at=stamp, name="   ")
    with pytest.raises(ValidationError):
        SpacePatch.model_validate({"expected_updated_at": stamp, "description": None})


def test_reordering_checks_a_complete_original_collection():
    from app.api.business_schemas import OrderRequest

    first, second = uuid4(), uuid4()
    request = OrderRequest(expected_order=[first, second], ordered_ids=[second, first])
    assert request.ordered_ids == [second, first]
    for payload in (
        {"expected_order": [first, second], "ordered_ids": [second]},
        {"expected_order": [first, first], "ordered_ids": [first, first]},
    ):
        with pytest.raises(ValidationError):
            OrderRequest.model_validate(payload)


def test_preview_is_read_only_and_mutations_require_publication_revision():
    from app.modules.content.schemas import (
        PublicationPreviewRequest,
        PublicationRequest,
        WithdrawRequest,
    )

    preview = PublicationPreviewRequest(expected_version=1)
    assert "request_id" not in preview.model_fields_set
    with pytest.raises(ValidationError):
        PublicationRequest.model_validate({"request_id": uuid4(), "expected_version": 1})
    request = PublicationRequest(
        request_id=uuid4(),
        expected_version=1,
        expected_publication_version=0,
    )
    assert request.expected_publication_version == 0
    with pytest.raises(ValidationError):
        WithdrawRequest.model_validate({"expected_published_content_version": 1})
    assert WithdrawRequest(expected_publication_version=2).expected_publication_version == 2


def test_refresh_uses_cookie_while_business_uses_bearer_and_logout_accepts_either():
    contract = record_contract()
    refresh = contract["paths"]["/api/auth/sessions/refresh"]["post"]
    assert refresh["security"] == [{"refreshCookie": []}]
    assert "requestBody" not in refresh
    assert {"401", "403", "429"} <= refresh["responses"].keys()
    assert "Set-Cookie" in refresh["responses"]["200"]["headers"]
    private = contract["paths"]["/api/contents"]["get"]
    assert private["security"] == [{"accessToken": []}]
    logout = contract["paths"]["/api/auth/sessions/current"]["delete"]
    assert logout["security"] == [{"accessToken": []}, {"refreshCookie": []}]
    assert contract["components"]["securitySchemes"]["refreshCookie"]["in"] == "cookie"
