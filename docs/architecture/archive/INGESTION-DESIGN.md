# 统一采集架构

2026-11-25 · 按用户确认采纳[调研报告](../product/deep-research-report.md)的采集模式。部署和数据库沿用已确认方案。字段设计仍需评审。

## 1. 管线

```mermaid
flowchart LR
    A[Studio 主动记录] --> I[Ingestion Contract]
    B[Markdown 和附件] --> I
    C[网页 URL] --> I
    D[ChatGPT 导出] --> I
    E[DOCX 和 PDF] --> I
    F[未来连接器] --> I
    I --> S[Source 来源与版本]
    S --> R[RawAsset 原始资料]
    S --> J[IngestionRun 处理尝试]
    R --> J
    J --> P[Parser Router]
    P --> N[NormalizedDocument 解析结果]
    N --> V[清洗与结构校验]
    V --> K[Content 可编辑记录]
    K --> Q[索引任务]
    Q --> T[搜索投影]
    Q -. 后续阶段 .-> U[Chunk 与向量索引]
```

首阶段不接 AI。统一契约包含所有者、输入类型、幂等键、来源标识、原始时间、原始载荷引用和权限。各入口共用来源追溯、幂等与保存规则。Studio 的 Tiptap 输入可同步完成规范化与保存，不必等待外部解析器；普通后续编辑直接修改 Content，按版本触发投影更新。

## 2. 对象边界与现有模型映射

| 对象 | 物理设计建议 | 与现有模型的关系 |
| --- | --- | --- |
| Source | sources | 外部来源身份，可独立于笔记存在；原 content_sources 改为内容到来源版本的引用 |
| SourceVersion | source_versions | 保留原始创建/更新时间、校验摘要和资料版本。重抓取或重新导入创建新版本 |
| RawAsset | raw_assets | 指向附件存储文件，保留原始 JSON、文件或网页快照及元数据；attachments 继续承接二进制存储，不重复保存文件 |
| IngestionJob | import_jobs / import_items | 继续承接批次与输入项，输入项关联 source_version_id |
| IngestionRun | ingestion_runs | 每次解析或重试的执行记录，保存解析器名称、版本、配置摘要、阶段、错误和租约 |
| NormalizedDocument | normalized_documents | 某次处理生成的不可变解析结果。与用户编辑正文分开 |
| Knowledge Item | contents / content_bodies | 复用原有记录和 Tiptap JSON 正文，保留 normalized_document_id 的来源引用 |
| IndexJob | index_jobs | 按内容版本记录投影/索引任务，通过事务性任务表可靠投递 |
| Chunk | 后续阶段定义 | 消费内容版本及哈希，不作为首阶段建表前提 |

SourceVersion 的原始资料和 NormalizedDocument 的解析结果不可被用户编辑覆盖。Content 是用户可修改的笔记。相同来源可以再次处理；从同一解析结果生成多份笔记必须为显式用户操作。

## 3. 数据字段建议

以下为新增表核心字段。实体均含 id UUID、owner_id、created_at；业务引用使用同所有者复合外键。

| 表 | 字段 | 备注 |
| --- | --- | --- |
| sources | kind、platform、external_id 可空、external_url 可空、privacy_scope | 来源身份；权限具体枚举待设计 |
| source_versions | source_id、revision、checksum、original_created_at 可空、original_updated_at 可空、captured_at、metadata JSONB | 唯一键 (source_id,revision)，原始资料版本 |
| raw_assets | source_version_id、attachment_id、asset_role、metadata JSONB | 原始对象及其附件引用 |
| ingestion_runs | import_item_id、source_version_id、attempt、parser_name、parser_version、config_hash、stage、status、lease_token 可空、lease_until 可空、error_code 可空、error_detail 可空、started_at 可空、finished_at 可空 | 唯一键 (import_item_id,attempt)，每次尝试保留历史 |
| normalized_documents | ingestion_run_id、source_version_id、canonical_format、schema_version、body JSONB、plain_text、content_hash、warnings JSONB | 每次输出的规范结果；复杂解析器原输出可另存为 raw_assets 的派生产物，原始对象角色须区分 |
| index_jobs | content_id、content_version、index_kind、processor_version、status、attempt_count、lease_token 可空、lease_until 可空、error_detail 可空 | 唯一键 (content_id,content_version,index_kind,processor_version)，可重试重建 |

sources 外部唯一性按平台和输入类型确定，URL 不能一概充当全局唯一键。source_versions 校验摘要用于判断变化；处理版本由解析器版本和配置摘要共同识别。规范内容 schema 与各解析器原生输出的转换规则需要接口契约进一步细化。

## 4. 保存、失败与重跑

- 输入接收成功先形成可追溯的来源和原始资料。上传成功与解析成功分别反馈。
- 解析阶段可产生 success、partial、failed、needs_review 等结果，状态与阶段分别保存。批次状态聚合输入项，不直接等同于处理尝试状态。
- 输入项完成时提交解析结果、内容来源引用与记录，再标记结果。相同幂等请求复用结果；重试创建新的 run，保留原尝试。
- 首次成功可创建 Content。已有笔记的重新解析先产生候选结果，不能静默覆盖用户编辑；确认应用需检查 expected_version。
- 复杂文件可先保留附件并允许查看处理结果。只有需要正文的功能依赖解析完成；失败不丢弃原件。
- 编辑正文、更新 plain_text 与插入 index_jobs 在同一数据库事务提交。plain_text 支撑首阶段直接搜索，后续异步索引失败也可重建。
- 索引 worker 按版本领取任务并校验租约。旧版本结果不可覆盖新版本索引；删除时阻止旧任务重新建立可搜索内容。
- 数据库任务表与一个 worker 作为初始实现建议。处理器须幂等，外部文件操作通过状态和补偿协调。

## 5. 输入适配与顺序

采用调研顺序作为工程实施基线，替代前文将导入整体后置的拆分。

1. 统一契约与来源/原件/版本/处理记录，Studio 主动记录贯通。
2. Markdown 与图片附件，保留 frontmatter、原路径、时间、附件和 wikilink。
3. URL Capture，先保留链接，抓取成功后留 HTML 快照，清洗并预览再生成内容。
4. ChatGPT 官方导出，完整保留 JSON、角色、顺序、分支和附件，支持分片输入的兼容验证。
5. Docling 的 DOCX/PDF 解析验证，反馈部分成功及结构丢失，OCR 与资源开销单独评估。

AI 对话仍是产品重要来源，优先级顺序体现实现依赖，具体阶段与承诺在路线图评审。解析库版本、维护情况与许可在引入时重新核验。

## 6. 格式与安全

用户正文权威格式仍为 Tiptap JSON。NormalizedDocument 是解析层的版本化契约，解析器原始 JSON 可以保留，不能把 Markdown 展示结果同时当另一份权威用户正文。MDX 采用后续受控组件方案。

网页抓取校验协议、解析后的 IP 与每次重定向，防止访问内网及元数据服务；限制响应大小、超时和递归附件。HTML 清洗后转换，禁止执行导入内容中的脚本。原始资料默认私有，原文保留和用户主动永久删除须兼容，不能把“保留原件”实现成无法删除。

未来 ConnectorAdapter 负责授权、变化枚举、抓取与游标。游标只在数据可靠保存后推进。外部删除记录 tombstone，由用户决定本地内容处理。首阶段暂不建立连接器或向量表。

## 7. 建表前验证

- 同一输入重试和 worker 中断不重复生成笔记。
- 解析器升级可重新运行，旧原件、旧结果与用户笔记都保留。
- 再次导入新增消息或修改文件能辨认版本差异。
- 部分解析、未知格式、缺失附件明确反馈。
- 用户编辑与重解析确认同时发生时检测冲突。
- 旧索引任务、已删除记录与原件清理符合权限和引用约束。

本稿确立采集边界，尚未执行迁移。数据库设计第 19 节列出对旧表设计的修订影响。
