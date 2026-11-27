# 灵脑（Luma）

灵脑是个人记录与知识工作台，用于保存笔记、AI 对话、工作经验、生活经历和思考，通过目录、搜索与关联找回过去的积累。

## 查看界面

打开 [Studio 原型](prototypes/studio/index.html) 查看页面与交互。原型数据保存在浏览器中，尚未连接后端；旧收集箱、归档、保存即更新公开内容等行为仍待改版；正式规则见产品需求。

## 当前可用能力

项目处于基础实现阶段，尚不能作为正式笔记应用使用。

| 能力 | 状态 |
| --- | --- |
| 数据库 | 23 张业务表与迁移可用 |
| 后端基础 | 配置、事务、健康检查和所有者初始化命令可用 |
| 业务 API | 登录、刷新、当前用户与退出可用，其余接口待实现 |
| Studio | 静态交互原型，正式前端待实现 |
| Site、AI、生产部署 | 后续阶段 |

## 快速开始

准备 Python 3.12+、uv 和已启动的 PostgreSQL。以下在仓库根目录使用 PowerShell：

```powershell
cd backend
uv sync --extra dev --extra test --locked
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

在 .env 填入数据库凭据，确保 luma_dev 已存在，再执行：

```powershell
$env:APP_ENV = 'development'
uv run --locked alembic upgrade head
uv run --locked uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000/docs 查看已实现的健康检查与认证接口。首次建库、测试及问题排查见 [开发指南](docs/development/DEVELOPMENT.md)。

## 文档

| 你想做什么 | 阅读入口 |
| --- | --- |
| 启动、测试或修改后端 | [开发指南](docs/development/DEVELOPMENT.md) |
| 查测试用例和人工验收结果 | [测试与验收](docs/development/TESTING.md) |
| 理解模块和数据流 | [系统设计](docs/architecture/ARCHITECTURE.md) |
| 核对功能范围和验收结果 | [产品需求](docs/product/PRD.md) |
| 查表、字段和约束 | [数据库设计](docs/architecture/DATABASE-DESIGN.md) |
| 查请求、响应和错误规则 | [API 契约](docs/architecture/API.md) |
| 设计或实现页面 | [设计规范](docs/design/DESIGN.md) |

[项目 Q&A](docs/QA.md) 记录关键困难和取舍，[变更记录](docs/CHANGELOG.md) 记录文档修订。旧方案保留在各主题 archive 目录，不作为现行规格。

## 下一步

接入 Studio 登录页，验证登录、刷新保持状态和退出，再按记录契约实现新建、保存、详情和列表。V1.0 保留人工思考主题、记录成员和时间线，并覆盖中英文及移动端核心操作。第一阶段不接 AI。
