"""迁移与测试共用的连接地址入口。"""

from sqlalchemy import URL

from app.core.config import Settings


def database_url() -> URL:
    return Settings.load().url()
