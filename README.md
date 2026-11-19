# 灵脑（Luma）

灵脑是面向个人长期使用的数字第二大脑。它帮助个人持续收集、组织、关联和找回工作、学习、生活与思考中的知识、资料、经历和想法，并在长期演进中把知识管理、个人第二大脑与个人 AI 助手接成同一套系统。

产品主张：让知识成为记忆，让记忆产生联系，让联系辅助思考。

V1.0 先做成个人知识管理工作台。体验分为私人 Studio 与公开 Explore：默认私有，由用户主动发布。目标平台是 Web，PC 优先，移动端保持基本可用。

## 当前阶段

仓库处于路线图中的 Phase 0：产品文档基线已经建立，Studio 有可在浏览器中打开的静态原型。前后端业务应用尚未开发，架构、设计规范和开发说明尚未编写。

V1.0 要打通两条闭环，验收标准见 [PRD](docs/product/PRD.md)：

- 私人知识闭环：快速记录或外部导入，经过收集、整理、编辑、关联和搜索，再导出与备份。
- 公开表达闭环：在 Studio 中创建并编辑，由用户主动发布到 Explore，之后可以更新或撤回。

## 文档

| 文档 | 说明 |
|---|---|
| [产品战略](docs/product/PRODUCT-STRATEGY.md) | 长期方向、定位、用户和产品承诺 |
| [产品需求](docs/product/PRD.md) | V1.0 范围、流程、业务规则和验收标准 |
| [产品路线图](docs/product/ROADMAP.md) | 从工作台到个人 AI 助手的阶段划分 |
| [核心领域模型](docs/product/CORE-DOMAIN-MODEL.md) | 内容、空间、来源、关联和发布的逻辑模型 |
| [文档变更记录](docs/CHANGELOG.md) | 产品文档的修订摘要 |
| [深度调研](docs/product/deep-research-report.md) | 开源项目与采集架构的调研材料，不是技术基线 |

已确认的十项产品决策写在 [PRD 第 2.2 节](docs/product/PRD.md)。技术选型、数据表和 API 契约待架构文档确认，不在本页展开。

## 目录

- `docs/product/`：产品战略、需求、路线图和领域模型。
- `docs/design/`：交互、视觉设计与设计规范。目录已保留，材料尚未写入。
- `docs/architecture/`：系统架构、技术选型与架构决策。目录已保留，材料尚未写入。
- `docs/development/`：开发流程、环境说明与实施计划。目录已保留，材料尚未写入。
- `prototypes/studio/`：灵脑 Studio 静态原型。

## Studio 原型

用浏览器直接打开 [prototypes/studio/index.html](prototypes/studio/index.html)。原型只演示界面和页面流转，不连接后端。

| 页面 | 文件 |
|---|---|
| 登录 | [login.html](prototypes/studio/login.html) |
| 控制台 | [index.html](prototypes/studio/index.html) |
| 收集箱 | [inbox.html](prototypes/studio/inbox.html) |
| 知识空间 | [spaces.html](prototypes/studio/spaces.html) |
| 空间详情 | [space.html](prototypes/studio/space.html) |
| 内容编辑 | [editor.html](prototypes/studio/editor.html) |
| 搜索 | [search.html](prototypes/studio/search.html) |
| 导入中心 | [imports.html](prototypes/studio/imports.html) |
| 学习中心 | [learning.html](prototypes/studio/learning.html) |
| 数据管理 | [data.html](prototypes/studio/data.html) |
| 回收站 | [trash.html](prototypes/studio/trash.html) |
| 外观设置 | [appearance.html](prototypes/studio/appearance.html) |
| 账户设置 | [settings.html](prototypes/studio/settings.html) |
