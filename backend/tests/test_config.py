"""环境隔离和生产配置失败必须可验证。"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import ConfigurationError, Settings


@pytest.fixture
def clean_environment(monkeypatch):
    for key in (
        "APP_ENV",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "CORS_ORIGINS",
    ):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_development_file_and_environment_precedence(tmp_path: Path, clean_environment):
    (tmp_path / ".env.development").write_text(
        "DB_USER=file_user\nDB_PASSWORD=hidden-secret\n", encoding="utf-8"
    )
    clean_environment.setenv("DB_USER", "override")
    settings = Settings.load(tmp_path)
    assert settings.user == "override"
    assert settings.name == "luma_dev"
    assert "hidden-secret" not in repr(settings)
    assert "hidden-secret" not in str(settings.url())


@pytest.mark.parametrize("port", ["abc", 0, 65536])
def test_invalid_port(port):
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="development",
            DB_NAME="luma_dev",
            DB_USER="user",
            DB_PASSWORD="secret",
            DB_PORT=port,
        )


def test_production_never_loads_dotenv(tmp_path: Path, clean_environment):
    (tmp_path / ".env.production").write_text(
        "DB_USER=user\nDB_PASSWORD=secret\n", encoding="utf-8"
    )
    clean_environment.setenv("APP_ENV", "production")
    with pytest.raises(ConfigurationError):
        Settings.load(tmp_path)


def test_production_requires_explicit_database():
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", DB_USER="luma_app", DB_PASSWORD="a-long-test-secret")


@pytest.mark.parametrize(
    "overrides", [{"DB_NAME": "luma_dev"}, {"DB_USER": "postgres"}, {"DB_PASSWORD": "123456"}]
)
def test_production_rejects_development_credentials(overrides):
    values = dict(
        APP_ENV="production",
        DB_HOST="db",
        DB_PORT=5432,
        DB_NAME="luma",
        DB_USER="luma_app",
        DB_PASSWORD="a-long-test-secret",
    )
    values.update(overrides)
    with pytest.raises(ValidationError):
        Settings(**values)


def test_production_accepts_explicit_configuration():
    settings = Settings(
        APP_ENV="production",
        DB_HOST="db",
        DB_PORT=5432,
        DB_NAME="luma",
        DB_USER="luma_app",
        DB_PASSWORD="a-long-test-secret",
    )
    assert settings.app_env == "production"


def test_invalid_environment(tmp_path: Path, clean_environment):
    clean_environment.setenv("APP_ENV", "typo")
    with pytest.raises(ConfigurationError, match="APP_ENV"):
        Settings.load(tmp_path)


def test_env_file_cannot_switch_selected_environment(tmp_path: Path, clean_environment):
    (tmp_path / ".env.development").write_text(
        "APP_ENV=production\nDB_USER=user\nDB_PASSWORD=secret\n", encoding="utf-8"
    )
    with pytest.raises(ConfigurationError):
        Settings.load(tmp_path)
