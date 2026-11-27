# 开发指南

以下命令使用 Windows PowerShell。除首次进入目录外，均在仓库的 backend 目录执行。

## 准备环境

安装 Python 3.12+、uv 和 PostgreSQL，并启动 PostgreSQL 服务。本机已验证 Python 3.14.6 与 PostgreSQL 16.14。本地开发不需要 Docker；前端尚未初始化，目前无需启动 Node 服务。

```powershell
cd backend
uv sync --extra dev --extra test --locked
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

编辑 .env，填写自己的 DB_USER、DB_PASSWORD。默认地址为 127.0.0.1:5432，库名 luma_dev，不把密码写进命令或 Git。

APP_ENV 默认 development。若已有 .env.development，它会优先于 .env；进程环境变量又优先于文件。修改配置未生效时先检查这两处覆盖来源。

## 初始化数据库

已有 luma_dev 时跳过建库，不要清空现有数据。新环境先在 PostgreSQL 中创建空库；createdb 命令位于 PostgreSQL 的 bin 目录：

```powershell
createdb -h 127.0.0.1 -p 5432 -U postgres luma_dev
```

命令交互式提示密码，不将密码作为参数。也可以用数据库客户端建空库。

应用迁移并检查模型差异：

```powershell
$env:APP_ENV = 'development'
uv run --locked alembic upgrade head
uv run --locked alembic current
uv run --locked alembic check
```

当前迁移终点是 782568a18b39，包含 22 张业务表。alembic check 应报告无新增升级操作；它检查模型差异，不检查数据是否完整。

## 启动后端

```powershell
uv run --locked uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

| 地址 | 预期结果 |
| --- | --- |
| http://127.0.0.1:8000/health/live | 200，返回 status=ok |
| http://127.0.0.1:8000/health/ready | 数据库可连接时 200，否则 503 |
| http://127.0.0.1:8000/docs | 开发接口文档，当前只有健康检查 |

记录、人工思考脉络和发布业务路由尚未实现。/api/contents、/api/threads 及发布路径当前返回 404。运行应用的 /openapi.json 只展示已注册的健康检查路由。

另开终端，在仓库根目录打开 prototypes/studio/index.html 查看静态原型。原型依赖浏览器存储，没有连接当前后端。

## 测试与代码检查

```powershell
$env:APP_ENV = 'development'
uv run --locked --extra test pytest -q
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev mypy
```

测试与开发共用 luma_dev，数据库用例通过事务回滚临时写入，不使用独立测试库。pytest 拒绝 production 配置，数据库用例还校验库名。健康检查测试只读取数据库。

Ruff 检查后端 Python 文件；mypy 严格检查 app、迁移环境与维护脚本，测试辅助函数和迁移版本文件暂不纳入类型检查。当前测试客户端会产生一条 Starlette/httpx 弃用提示；不影响测试断言，后续升级处理。

## 修改接口契约

请求响应模型在 app/modules/content/schemas.py 与 app/api/business_schemas.py，完整操作定义在 app/api/contract.py 和 business_contract.py。修改后重新导出，不手工编辑 JSON 产物：

```powershell
uv run --locked --extra test python -m scripts.export_openapi
uv run --locked --extra test python -m scripts.export_openapi --check
uv run --locked --extra test pytest tests/test_contract.py -q
```

运行应用的 /openapi.json 只包含已实现路由。契约覆盖 V1.0 的全部服务端业务操作，当前均标记 planned，尚未注册业务路由。契约中的路径表是接口定义，运行应用的 /docs 才反映已注册接口；具体行为见 [API 契约](../architecture/API.md)。

## 修改数据库结构

1. 修改 app/modules 对应领域的 models.py。
2. 确保模型由 app/db/models.py 注册。
3. 生成迁移，检查字段、约束、索引、备注及降级逻辑。
4. 应用迁移，再检查模型一致性和相关测试。

```powershell
uv run --locked alembic revision --autogenerate -m describe_change
uv run --locked alembic upgrade head
uv run --locked alembic check
uv run --locked --extra test pytest -q
```

已发布迁移不改写。自动生成不保证数据兼容，删除字段或数据迁移须先评估备份与恢复。

### 验证迁移回退

仅在没有业务数据、没有并行写入的本地开发库执行：

```powershell
uv run --locked python -m scripts.verify_migrations
```

脚本检查主机、库名、额外表和业务行数，然后删除并重建项目表；有数据时停止。此命令不属于普通测试，也不验证备份恢复。不要在日常使用的数据环境中执行。

## 本机生产与后续上云

开发和生产可以共用同一台机器、同一个 PostgreSQL 服务，但使用不同数据库。正式数据使用独立生产库（例如 luma），不写入 luma_dev。

生产配置通过进程变量注入，APP_ENV=production，不自动读取任何 .env。变量清单见 backend/.env.production.example；这是示例清单，不是自动加载文件。

生产必须显式提供 DB_HOST、DB_PORT、DB_NAME、DB_USER、DB_PASSWORD。当前校验拒绝 postgres 账号、开发库名及示例密码；账号实际权限仍需在 PostgreSQL 中配置。生产运行不使用 --reload，关闭 /docs 与 /openapi.json。

生产库、账号与 Docker/Compose 尚未部署。本机正式使用后迁云时，迁移生产数据并设置新的数据库和访问地址，继续使用同一份代码。

## 排查启动问题

| 现象 | 检查位置 |
| --- | --- |
| 配置校验失败 | .env / .env.development 与进程变量的覆盖关系；账号、密码和 APP_ENV |
| ready 返回 503 | PostgreSQL 服务、主机端口、库是否存在、连接凭据 |
| 找不到表 | 当前 DB_NAME，是否运行过 alembic upgrade head |
| createdb 找不到 | PostgreSQL bin 是否加入 PATH，或用数据库客户端建空库 |
| 8000 端口被占用 | 停止旧服务，或在启动命令中改 --port |
| 记录接口返回 404 | 当前业务路由尚未实现，不是数据库连接问题 |

模块职责和保存流程见 [系统设计](../architecture/ARCHITECTURE.md)。
