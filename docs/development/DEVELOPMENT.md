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

当前迁移终点是 9c3d8a1f6b20，包含 23 张业务表。认证迁移会使旧会话失效，账号与个人内容保留。alembic check 应报告无新增升级操作；它检查模型差异，不检查数据是否完整。

## 初始化所有者账号

数据库迁移完成后，在交互式终端运行一次：

```powershell
uv run --locked python -m scripts.init_owner
```

按提示输入登录账号、显示名称和两次密码。密码输入不回显，无法隐藏输入时命令停止。密码通过 pwdlib 生成 Argon2id 哈希后保存，成功只输出账号及用户 ID。数据库已有任意用户时拒绝初始化，不覆盖账号或密码；并发初始化通过事务内表锁保证只创建一位所有者。

新密码为 8–128 个字符；8–14 个字符须同时含字母和数字，15 个字符起不要求字符组合。支持中文和空格，不裁剪密码首尾空格，不接受全空白密码。规则在代码中统一维护，不提供密码长度设置项。

退出码 0 表示成功，2 表示输入不符合要求，1 表示取消、已有用户或配置与数据库错误。生产环境使用相同命令，配置来源遵循下文生产环境规则。该命令不提供公开注册接口。

## 启动后端

```powershell
uv run --locked uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

| 地址 | 预期结果 |
| --- | --- |
| http://127.0.0.1:8000/health/live | 200，返回 status=ok |
| http://127.0.0.1:8000/health/ready | 数据库可连接时 200，否则 503 |
| http://127.0.0.1:8000/docs | 开发接口文档，包含健康检查和四个认证接口 |

记录、人工思考脉络和发布业务路由尚未实现。/api/contents、/api/threads 及发布路径当前返回 404。运行应用的 /openapi.json 展示健康检查以及登录、刷新、当前用户和退出路由。

另开终端，在仓库根目录打开 prototypes/studio/index.html 查看静态原型。原型依赖浏览器存储，没有连接当前后端。

## 认证接入说明

登录接口的操作步骤、预期结果及页面验收统一见 [测试与验收](TESTING.md#登录)。

浏览器前端统一使用 credentials: include，并将实际前端来源加入 CORS_ORIGINS。登录、刷新和 Cookie 退出要求 Origin，缺失或不允许返回 403；Bearer 退出不依赖 Cookie。localhost 与 127.0.0.1 不要混用，开发时使用 Vite 代理将 /api 转发到后端，或保持前后端主机名相同。

默认 Access Token 15 分钟、刷新空闲期 7 天、会话绝对期限 30 天，对应 ACCESS_TOKEN_SECONDS、REFRESH_IDLE_SECONDS、SESSION_MAX_SECONDS。AUTH_ISSUER 默认 luma，AUTH_AUDIENCE 默认 luma-studio。AUTH_SIGNING_KEY 至少 32 字节，建议用 Python secrets.token_urlsafe(48) 生成并通过环境变量注入。开发未配置时每个进程生成临时密钥，重启后旧 Access Token 失效，可以使用有效刷新 Cookie 换取新令牌；生产必须显式提供稳定随机密钥，不自动生成或落盘。

当前限流为单进程内存计数，登录每个连接 IP 每 5 分钟 10 次，进程总计 100 次；刷新每个 IP 每分钟 60 次，进程总计 600 次，超限返回 429 与 Retry-After。当前以单 worker 运行；多进程或多实例部署前改为共享限流。只使用应用看到的连接 IP，不在业务代码读取任意 X-Forwarded-For，反向代理部署时明确配置可信代理。

## 测试与代码检查

```powershell
$env:APP_ENV = 'development'
uv run --locked --extra test pytest -q
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev mypy
```

核心验收场景和执行结果统一维护在 [测试与验收](TESTING.md)。

Ruff 检查后端 Python 文件；mypy 严格检查 app、迁移环境与维护脚本，测试辅助函数和迁移版本文件暂不纳入类型检查。当前测试客户端会产生一条 Starlette/httpx 弃用提示；不影响测试断言，后续升级处理。

## 修改接口契约

请求响应模型在 app/modules/content/schemas.py 与 app/api/business_schemas.py，完整操作定义在 app/api/contract.py 和 business_contract.py。修改后重新导出，不手工编辑 JSON 产物：

```powershell
uv run --locked --extra test python -m scripts.export_openapi
uv run --locked --extra test python -m scripts.export_openapi --check
uv run --locked --extra test pytest tests/test_contract.py -q
```

运行应用的 /openapi.json 只包含已实现路由。契约覆盖 V1.0 的全部服务端业务操作，其中四个认证操作标记 implemented，其余标记 planned。契约中的路径表是接口定义，运行应用的 /docs 才反映已注册接口；具体行为见 [API 契约](../architecture/API.md)。

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

生产必须显式提供 DB_HOST、DB_PORT、DB_NAME、DB_USER、DB_PASSWORD 和 AUTH_SIGNING_KEY。当前校验拒绝 postgres 账号、开发库名及示例密码；账号实际权限仍需在 PostgreSQL 中配置。生产运行不使用 --reload，关闭 /docs 与 /openapi.json。

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
