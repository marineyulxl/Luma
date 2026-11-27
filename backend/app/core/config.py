"""环境选择由进程 APP_ENV 决定，生产环境不读取本地 dotenv。"""

import os
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

BACKEND_DIR = Path(__file__).resolve().parents[2]
Environment = Literal["development", "production"]


class ConfigurationError(ValueError):
    """安全的配置错误，不输出凭据值。"""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore", populate_by_name=True, hide_input_in_errors=True, frozen=True
    )
    app_env: Environment = Field(default="development", validation_alias="APP_ENV")
    host: str = Field(default="127.0.0.1", min_length=1, validation_alias="DB_HOST")
    port: int = Field(default=5432, ge=1, le=65535, validation_alias="DB_PORT")
    name: str = Field(default="luma_dev", min_length=1, validation_alias="DB_NAME")
    user: str = Field(min_length=1, validation_alias="DB_USER")
    password: SecretStr = Field(validation_alias="DB_PASSWORD", repr=False)
    cors_origins: list[str] = Field(default_factory=list, validation_alias="CORS_ORIGINS")

    @model_validator(mode="after")
    def validate_environment(self) -> Self:
        if not self.password.get_secret_value() or not self.user.strip():
            raise ValueError("DB_USER 和 DB_PASSWORD 不能为空")
        if not self.host.strip() or not self.name.strip():
            raise ValueError("DB_HOST 和 DB_NAME 不能为空")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS 必须为明确的来源列表")
        if self.app_env == "production":
            required = {"host", "port", "name", "user", "password"}
            if not required.issubset(self.model_fields_set):
                raise ValueError("production 必须显式设置全部 DB_* 配置")
            if self.name in {"luma_dev", "luma_test", "postgres"} or self.user == "postgres":
                raise ValueError("production 必须使用独立业务数据库和受限账号")
            if self.password.get_secret_value() in {"123456", "password", "changethis"}:
                raise ValueError("production 不允许使用示例密码")
        return self

    @classmethod
    def load(cls, env_dir: Path = BACKEND_DIR) -> "Settings":
        environment = os.environ.get("APP_ENV", "development")
        if environment not in {"development", "production"}:
            raise ConfigurationError("APP_ENV 必须为 development 或 production")
        env_file: Path | None = None
        if environment != "production":
            env_file = env_dir / f".env.{environment}"
            # 兼容原来的本地开发配置。
            if environment == "development" and not env_file.exists():
                env_file = env_dir / ".env"
        try:
            result = cls(_env_file=env_file, _env_file_encoding="utf-8")
        except ValidationError as error:
            fields = sorted(
                {str(item["loc"][0]) if item["loc"] else "环境规则" for item in error.errors()}
            )
            raise ConfigurationError("配置校验失败，请检查：" + ", ".join(fields)) from None
        if result.app_env != environment:
            raise ConfigurationError("dotenv 中的 APP_ENV 与进程选择不一致")
        return result

    def url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
            query={"connect_timeout": "5"},
        )
