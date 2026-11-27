"""自动化测试只允许使用开发配置，数据由各用例事务回滚。"""

import os

import pytest

if os.environ.get("APP_ENV", "development") != "development":
    raise pytest.UsageError("pytest 只允许在 development 环境运行，禁止使用生产配置")
os.environ["APP_ENV"] = "development"
