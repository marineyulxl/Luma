"""所有者初始化的输入、密码保存、并发与命令入口回归验证。"""

import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from getpass import GetPassWarning
from threading import Barrier
from unittest.mock import Mock

import pytest
from pwdlib import PasswordHash
from pydantic import SecretStr, ValidationError
from sqlalchemy import event, func, select

from app.core.config import Settings
from app.modules.accounts.models import User
from app.modules.accounts.schemas import OwnerCreate
from app.modules.accounts.service import OwnerAlreadyInitializedError, initialize_owner
from scripts import init_owner

TEST_PASSWORD = "For local tests only 42"


def owner_request(username="owner"):
    return OwnerCreate(
        username=username, display_name="测试所有者", password=SecretStr(TEST_PASSWORD)
    )


@pytest.mark.parametrize("password", ["abc12345", "中文密码1234", "long phrase without digits"])
def test_owner_password_accepts_supported_forms(password):
    request = OwnerCreate(
        username=" owner ", display_name=" 显示名称 ", password=SecretStr(password)
    )
    assert request.username == "owner"
    assert request.display_name == "显示名称"
    assert password not in repr(request)


@pytest.mark.parametrize("password", ["abc1234", "abcdefgh", "12345678", " " * 20, "a" * 129])
def test_owner_password_rejects_invalid_values_without_echoing_them(password):
    with pytest.raises(ValidationError) as error:
        OwnerCreate(username="owner", display_name="Owner", password=SecretStr(password))
    assert password not in str(error.value)


@pytest.mark.parametrize("username", ["", "   ", "two words", "owner\nname"])
def test_owner_username_rejects_empty_or_ambiguous_names(username):
    with pytest.raises(ValidationError):
        OwnerCreate(username=username, display_name="Owner", password=SecretStr(TEST_PASSWORD))


def test_owner_is_committed_with_a_verifiable_argon2_hash(owner_database):
    factory, _ = owner_database
    result = initialize_owner(factory, owner_request())
    with factory() as session:
        owner = session.get(User, result.id)
        assert owner is not None
        assert owner.username == result.username
        assert owner.password_hash.startswith("$argon2id$")
        assert PasswordHash.recommended().verify(TEST_PASSWORD, owner.password_hash)
        assert not PasswordHash.recommended().verify("different password", owner.password_hash)
    assert not hasattr(result, "password_hash")


def test_second_initialization_preserves_existing_owner_and_hash(owner_database):
    factory, _ = owner_database
    result = initialize_owner(factory, owner_request())
    with factory() as session:
        original_hash = session.scalar(select(User.password_hash).where(User.id == result.id))
    with pytest.raises(OwnerAlreadyInitializedError):
        initialize_owner(factory, owner_request("another-owner"))
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert (
            session.scalar(select(User.password_hash).where(User.id == result.id)) == original_hash
        )


def test_failed_commit_leaves_no_owner(owner_database):
    factory, _ = owner_database

    def fail_commit(session):
        raise RuntimeError("test commit failure")

    event.listen(factory, "before_commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="test commit failure"):
            initialize_owner(factory, owner_request())
    finally:
        event.remove(factory, "before_commit", fail_commit)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_concurrent_initializations_create_only_one_owner(owner_database):
    factory, _ = owner_database
    barrier = Barrier(2)

    def attempt(username):
        barrier.wait(timeout=5)
        try:
            return initialize_owner(factory, owner_request(username))
        except OwnerAlreadyInitializedError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ["first-owner", "second-owner"]))
    assert sum(result is not None for result in results) == 1
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1


def test_cli_creates_owner_and_does_not_print_credentials(owner_database, monkeypatch, capsys):
    factory, engine = owner_database
    monkeypatch.setattr(
        sys, "argv", ["init_owner", "--username", "owner", "--display-name", "所有者"]
    )
    monkeypatch.setattr(init_owner, "getpass", lambda prompt: TEST_PASSWORD)
    monkeypatch.setattr(init_owner, "build_engine", lambda settings: engine)
    assert init_owner.main() == 0
    output = capsys.readouterr()
    assert "owner" in output.out
    assert TEST_PASSWORD not in output.out + output.err
    assert "$argon2" not in output.out + output.err
    with factory() as session:
        assert session.scalar(select(User.username)) == "owner"


@pytest.mark.parametrize("mode", ["mismatch", "echo", "cancel"])
def test_cli_stops_before_opening_database_on_input_errors(mode, monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["init_owner", "--username", "owner", "--display-name", "所有者"]
    )
    settings = Settings(DB_USER="test", DB_PASSWORD="test-only-password")
    monkeypatch.setattr(init_owner.Settings, "load", lambda: settings)
    build = Mock()
    monkeypatch.setattr(init_owner, "build_engine", build)
    passwords = iter([TEST_PASSWORD, "not the same password"])

    def read_password(prompt):
        if mode == "echo":
            warnings.warn("terminal cannot hide input", GetPassWarning, stacklevel=2)
        if mode == "cancel":
            raise EOFError
        return next(passwords)

    monkeypatch.setattr(init_owner, "getpass", read_password)
    assert init_owner.main() != 0
    build.assert_not_called()
    output = capsys.readouterr()
    assert TEST_PASSWORD not in output.out + output.err
