> 历史归档（2026-11-26）：保留原文，不再维护；现行规则见 [主文档](../../architecture/ARCHITECTURE.md)。原文中的旧路径、阶段和结论仅供回溯。

# 数据库开发

数据库规格见 [数据库设计](../architecture/DATABASE-DESIGN.md)。已实现模型、迁移、应用工厂及健康检查；记录业务 API 尚未实现，契约见 [API 契约](../architecture/API.md)。

## 环境

Python 3.12 及以上、uv、PostgreSQL。当前本地验证环境为 Python 3.14.6、PostgreSQL 16.14。

在仓库 backend 目录执行：

```powershell
uv sync --extra test --extra dev --locked
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

已有 .env 时保留原文件，密码只放在被 Git 忽略的本地配置或部署密钥中。

### 开发与生产

当前只区分 development、production 两种环境。开发与自动化测试共用本地 luma_dev，测试用例的写入在结束时回滚，不单独维护测试库。测试入口拒绝 APP_ENV=production；数据库测试还会检查库名。

APP_ENV 由进程环境变量决定，默认 development。开发配置优先读取 backend/.env.development，不存在时兼容读取 backend/.env；进程变量覆盖文件中的值。生产配置只读取进程环境变量，不回退读取任何本地 .env。

| 用途 | APP_ENV | 数据库 | 运行位置 |
| --- | --- | --- | --- |
| 开发及自动化测试 | development | luma_dev | 本机 |
| 正式使用 | production | luma（生产库名称） | 先本机，后续迁云 |

生产与开发可以使用同一个本机 PostgreSQL 服务，但必须使用独立数据库，正式数据不放入 luma_dev。生产库和生产账号当前尚未创建。生产配置显式提供全部 DB_*；校验拒绝开发库名、postgres 账号及示例密码，不代替数据库权限配置。

backend/.env.production.example 仅列出生产配置变量，不会被程序自动加载。先本机生产、后云服务器都使用相同的 APP_ENV=production；上云迁移生产数据、设置新连接及访问地址，业务代码不区分本机或云。

### 应用启动

在 backend 目录，本地开发：

```powershell
$env:APP_ENV = 'development'
uv run --locked uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

生产运行使用同一个工厂入口，设置 APP_ENV=production 及独立的 DB_*，不使用 --reload。部署 Docker 时由容器注入变量；当前尚未编写或验证生产 Compose，不表示已部署。

GET /health/live 只检查进程响应；GET /health/ready 执行 SELECT 1 检查数据库连接。生产关闭 /docs 与 /openapi.json。健康检查不代表业务表迁移完整或记录功能已经实现。

## 目录与职责

```text
backend/
├── app/
│   ├── main.py                 # 应用工厂及 lifespan
│   ├── api/                    # 请求依赖、错误响应和健康检查
│   ├── core/config.py          # 环境配置及校验
│   ├── db/
│   │   ├── base.py             # 共享 Base 和约束命名
│   │   ├── models.py           # 全部模型注册入口
│   │   └── session.py          # Engine、Session 工厂及事务上下文
│   └── modules/
│       ├── accounts/models.py
│       ├── organization/models.py
│       ├── content/models.py
│       ├── attachments/models.py
│       └── ingestion/models.py
├── migrations/
├── scripts/
└── tests/
```

模型类使用单数名称，数据库表名保持原样。各模块仅引用共享 Base，跨模块数据库关联通过表名外键表达，避免 Python 循环导入。迁移统一加载模型注册入口。

Settings 使用 pydantic-settings 校验配置，密码使用 SecretStr，不输出原始凭据。导入模块不创建连接；应用工厂在调用时读取配置。

应用启动时创建一个 Engine 和 Session 工厂，退出时释放 Engine；使用 transaction(factory) 为一个业务用例建立事务，成功提交、异常回滚并关闭 Session。当前为同步连接；数据库健康检查使用 def 路由，在线程池执行，避免阻塞事件循环。请求依赖只负责关闭 Session，不隐式提交；业务服务显式决定事务边界。

## 代码检查

在 backend 目录执行：

```powershell
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev mypy
```

Ruff 覆盖后端 Python 文件；mypy 严格检查 app、迁移环境及维护脚本，暂不包含测试辅助函数和生成的迁移版本。依赖由 uv.lock 锁定。

## 执行迁移

```powershell
uv run --extra test alembic upgrade head
uv run --extra test alembic current
uv run --extra test alembic check
```

模型按领域放在 backend/app/modules/*/models.py，backend/app/db/models.py 是统一注册入口；迁移位于 backend/migrations/versions/。迁移通过环境变量连接数据库，不使用 create_all 自动建表。

后续改表先修改模型，再生成并审阅迁移：

```powershell
uv run --extra test alembic revision --autogenerate -m describe_change
```

已发布的迁移不得修改。自动生成后检查约束、默认值、注释、索引及降级过程。删除数据前另行备份。

## 验证

```powershell
uv run --extra test pytest -q
```

测试仅允许连接 luma_dev，每个用例都在结束时回滚。测试中的版本校验验证条件更新可以拒绝旧版本；真实多连接并发和业务接口行为另行测试。

仅在本地无业务数据的开发库中验证整条迁移链：

```powershell
uv run --extra test python scripts/verify_migrations.py
```

该脚本检查库名、主机、额外表和业务表数据；满足条件后删除并重建项目表，最后运行模型一致性检查。有业务数据时停止。此操作不是备份恢复测试，不要用于正在写入数据的环境。

当前 36 项测试通过，覆盖数据库约束、配置与生产边界、Session 事务、应用资源释放、健康检查、错误响应以及契约验证。测试依赖产生一条 Starlette 关于 httpx 的弃用提示，不影响当前断言；升级测试客户端时处理。

## 服务层写入要求

- 同一事务保存 Content、Body、plain_text 与版本索引任务。
- 更新显式携带 owner_id 和预期 version，成功后增加 version 并更新 updated_at；数据库不会自动维护这些业务字段。
- JSONB 更新应赋予新值；当前模型未配置嵌套 JSON 原地变更跟踪。
- 租约 token、到期时间和状态同事务更新，完成前重新校验 token、到期时间和内容版本。
- 数据库复合外键防止跨所有者关联，但不替代 API 查询权限过滤。
