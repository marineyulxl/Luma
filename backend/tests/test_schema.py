"""真实 PostgreSQL 集成测试；每个用例结束回滚，不保留测试数据。"""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, insert, inspect, select, text, update
from sqlalchemy.exc import IntegrityError

from app.db.config import database_url
from app.db.models import (
    Base,
    Category,
    Content,
    ContentBody,
    ContentRelation,
    IndexJob,
    RefreshToken,
    SessionToken,
    Space,
    User,
)


@pytest.fixture
def db():
    url = database_url()
    if url.database != "luma_dev":
        pytest.fail("集成测试仅允许连接 luma_dev")
    engine = create_engine(url)
    with engine.connect() as conn:
        tx = conn.begin()
        try:
            yield conn
        finally:
            tx.rollback()
    engine.dispose()


def add(db, model, **values):
    return db.execute(insert(model).values(**values).returning(model.__table__)).mappings().one()


def user(db):
    return add(db, User, username=str(uuid4()), password_hash="test-only", display_name="测试")[
        "id"
    ]


def record(db, owner, **values):
    return add(
        db, Content, owner_id=owner, create_request_id=uuid4(), create_request_hash="test", **values
    )["id"]


def rejects(db, operation, code):
    with pytest.raises(IntegrityError) as error:
        with db.begin_nested():
            operation()
    assert error.value.orig.sqlstate == code


def test_tables_and_comments(db):
    inspector = inspect(db)
    assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
    for name, table in Base.metadata.tables.items():
        assert inspector.get_table_comment(name)["text"] == table.comment
        assert all(c["comment"] for c in inspector.get_columns(name))


def test_owner_boundary(db):
    a, b = user(db), user(db)
    space = add(db, Space, owner_id=a, name="工作", name_key="work")["id"]
    rejects(db, lambda: record(db, b, space_id=space), "23503")


def test_category_must_belong_to_space(db):
    owner = user(db)
    a = add(db, Space, owner_id=owner, name="A", name_key="a")["id"]
    b = add(db, Space, owner_id=owner, name="B", name_key="b")["id"]
    category = add(db, Category, owner_id=owner, space_id=a, name="笔记", name_key="note")["id"]
    rejects(db, lambda: record(db, owner, space_id=b, category_id=category), "23503")
    rejects(db, lambda: record(db, owner, category_id=category), "23514")
    record(db, owner, space_id=a, category_id=category)


def test_create_idempotency(db):
    owner, request = user(db), uuid4()
    values = dict(owner_id=owner, create_request_id=request, create_request_hash="same")
    add(db, Content, **values)
    rejects(db, lambda: add(db, Content, **values), "23505")


@pytest.mark.parametrize("body", [{}, [], {"type": "paragraph"}])
def test_invalid_body_rejected(db, body):
    owner = user(db)
    content = record(db, owner)
    rejects(
        db,
        lambda: add(
            db, ContentBody, owner_id=owner, content_id=content, body_json=body, plain_text=""
        ),
        "23514",
    )


def test_version_compare_and_swap(db):
    owner = user(db)
    content = record(db, owner)
    stmt = (
        update(Content)
        .where(Content.id == content, Content.owner_id == owner, Content.version == 1)
        .values(title="新版", version=2)
    )
    assert db.execute(stmt).rowcount == 1
    assert db.execute(stmt).rowcount == 0  # 旧版本无法覆盖新版


def test_soft_delete_restore_and_body_cascade(db):
    owner = user(db)
    content = record(db, owner)
    add(
        db,
        ContentBody,
        owner_id=owner,
        content_id=content,
        body_json={"type": "doc", "content": []},
        plain_text="",
    )
    db.execute(update(Content).where(Content.id == content).values(deleted_at=datetime.now(UTC)))
    assert (
        db.scalar(select(ContentBody.content_id).where(ContentBody.content_id == content))
        == content
    )
    db.execute(update(Content).where(Content.id == content).values(deleted_at=None))
    assert db.scalar(select(Content.deleted_at).where(Content.id == content)) is None
    db.execute(delete(Content).where(Content.id == content))
    assert (
        db.scalar(select(ContentBody.content_id).where(ContentBody.content_id == content)) is None
    )


def test_relation_deduplication(db):
    owner = user(db)
    a, b = sorted([record(db, owner), record(db, owner)])
    values = dict(owner_id=owner, from_content_id=a, to_content_id=b, relation_type="related_to")
    add(db, ContentRelation, **values)
    rejects(db, lambda: add(db, ContentRelation, **values), "23505")
    rejects(
        db,
        lambda: add(
            db,
            ContentRelation,
            owner_id=owner,
            from_content_id=b,
            to_content_id=a,
            relation_type="related_to",
        ),
        "23514",
    )


def test_index_lease_and_idempotency(db):
    owner = user(db)
    content = record(db, owner)
    values = dict(
        owner_id=owner,
        content_id=content,
        content_version=1,
        index_kind="search",
        processor_version="v1",
    )
    rejects(db, lambda: add(db, IndexJob, **values, status="processing"), "23514")
    task = add(db, IndexJob, **values)["id"]
    rejects(db, lambda: add(db, IndexJob, **values), "23505")
    token = uuid4()
    db.execute(
        update(IndexJob)
        .where(IndexJob.id == task)
        .values(status="processing", lease_token=token, lease_until=datetime.now(UTC))
    )
    stale = (
        update(IndexJob)
        .where(IndexJob.id == task, IndexJob.lease_token == uuid4())
        .values(status="success", lease_token=None, lease_until=None)
    )
    assert db.execute(stale).rowcount == 0
    assert (
        db.execute(
            update(IndexJob)
            .where(IndexJob.id == task, IndexJob.lease_token == token)
            .values(status="success", lease_token=None, lease_until=None)
        ).rowcount
        == 1
    )


def test_transaction_rollback(db):
    owner = user(db)
    with db.begin_nested() as savepoint:
        content = record(db, owner)
        savepoint.rollback()
    assert db.scalar(select(Content.id).where(Content.id == content)) is None


def test_ingestion_source_chain(db):
    from app.db.models import (
        ContentSource,
        ImportItem,
        ImportJob,
        IngestionRun,
        NormalizedDocument,
        Source,
        SourceVersion,
    )

    owner = user(db)
    source = add(db, Source, owner_id=owner, kind="markdown")["id"]
    versions = [
        add(
            db,
            SourceVersion,
            owner_id=owner,
            source_id=source,
            revision=n,
            checksum=str(n),
            captured_at=datetime.now(UTC),
        )["id"]
        for n in (1, 2)
    ]
    job = add(db, ImportJob, owner_id=owner, kind="markdown", idempotency_key=str(uuid4()))["id"]
    item = add(
        db, ImportItem, owner_id=owner, job_id=job, source_version_id=versions[0], item_key="1"
    )["id"]
    values = dict(
        owner_id=owner,
        import_item_id=item,
        source_version_id=versions[0],
        attempt=1,
        parser_name="markdown",
        parser_version="1",
        config_hash="test",
        stage="normalize",
        status="success",
    )
    run = add(db, IngestionRun, **values)["id"]
    rejects(db, lambda: add(db, IngestionRun, **values), "23505")
    wrong = dict(values, attempt=2, source_version_id=versions[1])
    rejects(db, lambda: add(db, IngestionRun, **wrong), "23503")
    result = add(
        db,
        NormalizedDocument,
        owner_id=owner,
        ingestion_run_id=run,
        source_version_id=versions[0],
        canonical_format="tiptap",
        schema_version=1,
        body={"type": "doc"},
        plain_text="",
        content_hash="test",
    )["id"]
    content = record(db, owner)
    rejects(
        db,
        lambda: add(
            db,
            ContentSource,
            owner_id=owner,
            content_id=content,
            source_version_id=versions[1],
            normalized_document_id=result,
        ),
        "23503",
    )
    add(
        db,
        ContentSource,
        owner_id=owner,
        content_id=content,
        source_version_id=versions[0],
        normalized_document_id=result,
    )
    rejects(
        db,
        lambda: db.execute(delete(SourceVersion).where(SourceVersion.id == versions[0])),
        "23503",
    )


def test_session_transaction_commit_and_rollback(db):
    from sqlalchemy.orm import Session, sessionmaker

    from app.db.session import transaction

    # Session commits release savepoints; the test's outer transaction still rolls back.
    factory = sessionmaker(
        bind=db, class_=Session, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    owner = uuid4()
    with transaction(factory) as session:
        session.add(User(id=owner, username=str(owner), password_hash="test", display_name="测试"))
    assert db.scalar(select(User.id).where(User.id == owner)) == owner
    failed = uuid4()
    with pytest.raises(RuntimeError, match="abort"):
        with transaction(factory) as session:
            session.add(
                User(id=failed, username=str(failed), password_hash="test", display_name="测试")
            )
            session.flush()
            raise RuntimeError("abort")
    assert db.scalar(select(User.id).where(User.id == failed)) is None


@pytest.fixture
def migration_schema(db):
    # All DDL and test rows remain inside the existing rollback-only transaction.
    schema = "auth_migration_" + uuid4().hex
    db.execute(text(f'CREATE SCHEMA "{schema}"'))
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["connection"] = db
    return cfg


@pytest.mark.parametrize("expired", [False, True])
def test_auth_migration_preserves_data_and_never_reactivates_legacy_sessions(
    db, migration_schema, expired
):
    public_revision = db.scalar(text("SELECT version_num FROM public.alembic_version"))
    command.upgrade(migration_schema, "782568a18b39")
    owner = user(db)
    content = record(db, owner, title="keep across migration")
    session_id = uuid4()
    now = datetime.now(UTC)
    db.execute(
        text("""
            INSERT INTO sessions (id, owner_id, token_hash, expires_at, created_at)
            VALUES (:id, :owner, 'legacy-test-only', :expires, :created)
        """),
        {
            "id": session_id,
            "owner": owner,
            "expires": now + timedelta(days=-1 if expired else 1),
            "created": now,
        },
    )
    command.upgrade(migration_schema, "head")
    session = db.execute(select(SessionToken).where(SessionToken.id == session_id)).mappings().one()
    assert session["revoked_at"] is not None
    assert session["revoked_reason"] == "legacy_upgrade"
    assert session["expires_at"] > session["created_at"]
    assert session["idle_expires_at"] == session["expires_at"]
    assert db.scalar(select(Content.title).where(Content.id == content)) == "keep across migration"
    assert db.scalar(select(User.id).where(User.id == owner)) == owner
    assert "token_hash" not in {c["name"] for c in inspect(db).get_columns("sessions")}
    command.downgrade(migration_schema, "782568a18b39")
    legacy = (
        db.execute(
            text("SELECT token_hash, revoked_at FROM sessions WHERE id=:id"), {"id": session_id}
        )
        .mappings()
        .one()
    )
    assert legacy["token_hash"].startswith("revoked:")
    assert legacy["revoked_at"] is not None
    assert not inspect(db).has_table("refresh_tokens")
    assert db.scalar(select(Content.title).where(Content.id == content)) == "keep across migration"
    command.upgrade(migration_schema, "head")
    assert (
        db.scalar(select(SessionToken.revoked_reason).where(SessionToken.id == session_id))
        == "legacy_upgrade"
    )
    assert db.scalar(text("SELECT version_num FROM public.alembic_version")) == public_revision


def login_session(db, owner):
    now = datetime.now(UTC)
    return add(
        db,
        SessionToken,
        owner_id=owner,
        created_at=now,
        last_refreshed_at=now,
        idle_expires_at=now + timedelta(days=1),
        expires_at=now + timedelta(days=2),
    )


def refresh_token(db, owner, session_id, **values):
    now = datetime.now(UTC)
    payload = {
        "owner_id": owner,
        "session_id": session_id,
        "token_hash": sha256(uuid4().bytes).hexdigest(),
        "created_at": now,
        "expires_at": now + timedelta(hours=1),
    }
    payload.update(values)
    return add(db, RefreshToken, **payload)


def test_auth_session_expiry_and_revocation_constraints(db):
    session = login_session(db, user(db))
    changes = (
        {"expires_at": session["created_at"]},
        {"idle_expires_at": session["expires_at"] + timedelta(seconds=1)},
        {"last_refreshed_at": session["created_at"] - timedelta(seconds=1)},
        {"revoked_at": datetime.now(UTC)},
        {"revoked_reason": "logout"},
        {"revoked_at": datetime.now(UTC), "revoked_reason": "unknown"},
    )
    for values in changes:
        rejects(
            db,
            lambda values=values: db.execute(
                update(SessionToken).where(SessionToken.id == session["id"]).values(**values)
            ),
            "23514",
        )


def test_refresh_history_constraints_and_session_cascade(db):
    owner, other_owner = user(db), user(db)
    session = login_session(db, owner)
    other_session = login_session(db, owner)
    foreign_session = login_session(db, other_owner)
    rejects(db, lambda: refresh_token(db, owner, session["id"], token_hash="raw-token"), "23514")
    root = refresh_token(db, owner, session["id"])
    rejects(db, lambda: refresh_token(db, owner, session["id"]), "23505")
    rejects(
        db,
        lambda: refresh_token(db, owner, other_session["id"], token_hash=root["token_hash"]),
        "23505",
    )
    rejects(db, lambda: refresh_token(db, owner, foreign_session["id"]), "23503")
    rejects(
        db, lambda: refresh_token(db, owner, other_session["id"], parent_id=root["id"]), "23503"
    )
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == root["id"])
        .values(consumed_at=datetime.now(UTC))
    )
    child = refresh_token(db, owner, session["id"], parent_id=root["id"])
    rejects(db, lambda: refresh_token(db, owner, session["id"], parent_id=root["id"]), "23505")
    assert (
        db.scalar(select(RefreshToken.parent_id).where(RefreshToken.id == child["id"]))
        == root["id"]
    )
    db.execute(delete(SessionToken).where(SessionToken.id == session["id"]))
    assert (
        db.scalar(select(RefreshToken.id).where(RefreshToken.session_id == session["id"])) is None
    )


def test_failed_rotation_rolls_back_parent_consumption(db):
    owner = user(db)
    session = login_session(db, owner)
    root = refresh_token(db, owner, session["id"])
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(
                update(RefreshToken)
                .where(RefreshToken.id == root["id"])
                .values(consumed_at=datetime.now(UTC))
            )
            refresh_token(db, owner, session["id"], parent_id=root["id"], token_hash="invalid")
    assert db.scalar(select(RefreshToken.consumed_at).where(RefreshToken.id == root["id"])) is None
