# 技术决策

## 已确认

| 项目 | 决定 | 确认日期 |
| --- | --- | --- |
| 数据库 | PostgreSQL | 2026-11-25 |
| 数据库访问与迁移 | SQLAlchemy 2.x、psycopg 3、Alembic | 2026-11-25 |
| 部署 | Docker，使用 Docker Compose 编排 | 2026-11-23 |
| 工程目录 | frontend/、backend/、deploy/ | 2026-11-23 |

## 前端命名与工程方案

公开端确定命名为 Site，工程名使用 site，私人工作台沿用 Studio / studio。

当前推荐将前端分成 frontend/studio（React + Vite）和 frontend/site（Next.js），共用 FastAPI 后端和 PostgreSQL。首阶段优先 Studio，Site 在公开发布阶段建设。该拆分是当前推荐方案，框架与版本最终确认后同步 PRD 原有 Next.js 统一前端描述。

## 数据库设计要求

- 正文采用 Tiptap JSON，数据库设计考虑使用 JSONB，具体字段由表结构设计落实。
- 即使首阶段只有一个所有者，也需考虑多标签页或多设备同时保存同一记录。
- 并发保存应检测版本冲突，避免旧内容静默覆盖新内容；版本字段和冲突响应待接口设计确定。
- 正文、元数据及关系的组合修改需明确事务边界。
- 索引围绕列表、搜索、位置与标签查询设计。中文检索方案待验证。

## 待确认

- PostgreSQL 版本及同步/异步数据库访问模式。
- 连接池及并发参数，依据部署资源和实际负载设置。
- 前端和后端具体版本、附件存储及备份方案。

领域关系见 [核心领域模型](../product/CORE-DOMAIN-MODEL.md)。

表结构设计见 [首阶段数据库设计](DATABASE-DESIGN.md)。
