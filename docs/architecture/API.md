# API 契约

## 范围与覆盖

本文定义 PRD 中 V1.0 的全部服务端业务接口。HTTP 方法、路径、请求响应模型、权限与操作规则共同组成契约，按 M0、Alpha、Beta、Release 分阶段实现。

机器定义见 [openapi.json](api/openapi.json)。记录、主题及发布模型维护在 backend/app/modules/content/schemas.py，其余接口模型维护在 backend/app/api/business_schemas.py；操作定义由 backend/app/api/contract.py 和 business_contract.py 汇总生成。公共错误模型位于 backend/app/api/schemas.py。运行状态和生成命令见 [开发指南](../development/DEVELOPMENT.md#修改接口契约)。

| PRD 能力 | 接口覆盖或使用方式 |
| --- | --- |
| ACC 账户 | 登录、刷新、退出、读取资料、修改名称与密码；初始化和管理员重置使用受保护命令，不提供公开注册或找回接口 |
| STU 首页 | 复用记录列表、搜索和主题列表；首页无需单独的统计接口 |
| INB 快速记录与全部记录 | 复用记录创建、列表与保存 |
| CNT 内容编辑 | 记录详情与保存、附件与 HTML 展示 |
| SPC 空间分类 | 空间和分类管理、空间排序、分类移动 |
| TYP 类型标签 | 固定类型读取、标签创建与维护，记录接口管理标签成员 |
| IMP 导入 | 资料预览、候选选择、提交批次、结果、重试、重解析与确认应用 |
| SRC 来源附件 | 来源身份和版本、记录来源引用、原始会话、文件上传下载 |
| SEA 搜索 | 私人组合搜索及摘要；Site 公开搜索 |
| REL 内容关联 | 创建、查看、移除关系及反向引用 |
| THR 人工思考脉络 | 主题、成员与时间线 |
| PUB 公开展示 | 私人预览、发布与更新、撤回、Site 列表详情与公开文件 |
| DAT 数据管理 | Markdown 导出、完整备份、校验预览和空白工作区恢复 |
| APP 外观及语言 | 当前浏览器保存偏好，复用前端资源，不增加云端偏好接口 |
| 后续 AI 能力 | V1.0 保留数据基础；LLM、RAG、Memory、Agent 的任务及确认协议按后续产品范围定义 |

## 通用约定

- 路径使用 /api，operationId 是稳定操作标识。私人接口由有效会话确定 owner_id，客户端不能指定数据所有者。
- 成功返回资源对象；分页返回 items、next_cursor。错误统一返回 code、message、details、current_version、current_updated_at。错误 code 为稳定字符串，客户端不依据中文提示分支。
- 不属于当前所有者的资源统一 404。公开接口只返回独立公开模型，即使调用者同时登录也不能扩展响应字段。
- 201 表示新资源已建立，202 表示任务已接收。两者返回 Location。异步任务成功以任务详情的 status 为准。相同 request_id、同一操作范围和相同规范化载荷重试返回 200 与原结果，载荷不同返回 409。
- DELETE 的重复请求按目标资源语义处理。已经消失且无法验证所有者的资源返回 404；仍有所有者身份和幂等记录的重复删除可返回原成功结果。不可绕过权限检查。
- 分页默认 30、最大 100；next_cursor 为不透明游标，绑定所有者、路径、筛选与排序。条件不匹配或无效游标返回 422。各列表不保证跨请求快照一致。
- 名称先去除首尾空白，再进行 Unicode 规范化和大小写规范化比较。空间在所有者内、分类在同父级内、标签在所有者内重名返回 409；不自动合并已有对象。
- 空间、分类和标签修改使用 expected_updated_at 与数据库更新时间匹配，时间由服务端原样返回。主题和记录使用 expected_version；版本冲突为 409。服务端验证最终合并状态并使用显式事务。
- 数组中的 ID 不允许重复，所有引用必须属于当前所有者；选择、重试及导出列表还须属于对应批次或工作区。不能信任前端传来的关联资源。
- 错误响应及日志不回显密码、令牌、数据库异常和存储内部路径。登录和刷新成功响应仅向当前客户端返回 Access Token，并设置 Cache-Control: no-store。附件名称清洗后用于下载头，禁止路径穿越和头注入。

| HTTP 状态 | 含义 |
| --- | --- |
| 200 | 读取、保存、预览或幂等重试成功 |
| 201 | 新建资源成功 |
| 202 | 异步任务已接收 |
| 204 | 删除、退出或密码修改成功，无响应体 |
| 401 | 登录失败或会话失效 |
| 403 | 已认证但被策略拒绝，例如跨站请求校验失败 |
| 404 | 资源不存在或不可见 |
| 409 | 并发、引用、幂等、非空目录或任务状态冲突 |
| 413 | 上传或请求超过配置上限 |
| 415 | 格式不支持 |
| 422 | 输入或组合条件非法 |
| 429 | 触发限流 |
| 500 / 503 | 内部错误或服务暂不可用 |

## 错误代码

| code | HTTP | 使用场景 |
| --- | --- | --- |
| invalid_credentials | 401 | 账号或密码错误，统一提示 |
| unauthenticated | 401 | 无会话或会话过期 |
| forbidden | 403 | 已认证请求被策略拒绝 |
| not_found | 404 | 资源不存在或不可见 |
| version_conflict | 409 | 记录或主题版本已变化 |
| timestamp_conflict | 409 | 空间、分类或标签已被修改，返回 current_updated_at |
| order_conflict | 409 | 空间完整顺序或集合已被其他操作改变 |
| publication_version_conflict | 409 | 发布状态版本已改变，current_version 返回当前 publication_version |
| idempotency_conflict | 409 | request_id 已用于不同载荷 |
| name_conflict | 409 | 同范围名称重复 |
| reference_conflict | 409 | 引用不存在、失效或被占用 |
| directory_not_empty | 409 | 空间或分类仍含记录或子级 |
| source_in_use | 409 | 来源仍被其他记录引用 |
| job_not_ready | 409 | 任务未完成，不能下载或应用 |
| preview_expired | 409 | 用户确认的预览已失效 |
| workspace_not_empty | 409 | 工作区不满足恢复条件 |
| workspace_restoring | 409 | 恢复期间拒绝其他写入 |
| validation_error | 422 | 字段或组合条件不符合要求 |
| invalid_cursor | 422 | 游标错误或与当前筛选不匹配 |
| invalid_backup | 422 | 备份损坏或格式不兼容 |
| payload_too_large | 413 | 请求或文件超过限制 |
| unsupported_media_type | 415 | 文件格式不支持 |
| rate_limited | 429 | 触发限流 |
| internal_error | 500 | 内部错误，响应不泄露内部细节 |
| unavailable | 503 | 依赖不可用 |

## 账户接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| POST | /api/auth/sessions | sessions_create | LoginRequest | 200 SessionDetail |
| POST | /api/auth/sessions/refresh | sessions_refresh | 无请求体 | 200 SessionDetail |
| DELETE | /api/auth/sessions/current | sessions_delete | 无请求体 | 204 无响应体 |
| GET | /api/account | account_detail | 无请求体 | 200 AccountDetail |
| PATCH | /api/account | account_update | AccountPatch | 200 AccountDetail |
| PUT | /api/account/password | account_password_update | PasswordChange | 204 无响应体 |

登录成功返回 SessionDetail，其中 access_token 为 JWT，token_type 为 Bearer，access_expires_in 为访问令牌剩余秒数，expires_at 为本次签发时绝对与空闲到期时间中较早的时刻。Access Token 仅放前端内存，刷新凭据由 Set-Cookie 写入 luma_refresh，设置 HttpOnly、Secure、SameSite=Lax、Path=/api/auth/sessions。正式部署使用 HTTPS，并限制明确允许的来源；本地 HTTP 开发单独配置 Cookie 的 Secure 行为。

业务接口使用 Authorization: Bearer，服务端验证签名算法白名单、签发方、受众和时效，并以 JWT 的 sid 检查会话是否仍有效。刷新接口只接受 Refresh Cookie，不要求有效 Access Token。刷新成功原子轮换随机令牌并签发新 Access Token，数据库只存刷新凭据哈希及轮换关系。旧刷新令牌重用时撤销对应会话族，前端通过统一刷新协调器及跨标签页同步避免并发刷新。刷新响应不确定时不得自动无限重放旧令牌。

登录、刷新及以 Cookie 退出时校验 Origin 和允许来源，跨域凭据请求使用明确来源的 CORS 配置。退出允许有效 Bearer 或刷新凭据，撤销当前会话并清除 Cookie；无有效凭据返回 401，前端仍清除内存。修改密码验证旧密码，成功后撤销全部会话并清除 Cookie。过期 JWT 不能阻止使用有效刷新凭据退出。

登录失败统一提示账号或密码错误并限流。单所有者初始化和管理员重置使用受保护命令。未来原生 App 的刷新凭据由系统安全存储承接，App 传输适配在对应客户端阶段定义。

## 空间、分类与标签接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| GET | /api/spaces | spaces_list | 无请求体，查询 limit、cursor | 200 SpacePage |
| POST | /api/spaces | spaces_create | SpaceCreate | 201 SpaceDetail；200 SpaceDetail |
| GET | /api/spaces/{space_id} | spaces_detail | 无请求体 | 200 SpaceDetail |
| PATCH | /api/spaces/{space_id} | spaces_update | SpacePatch | 200 SpaceDetail |
| DELETE | /api/spaces/{space_id} | spaces_delete | 无请求体，查询 expected_updated_at | 204 无响应体 |
| PUT | /api/spaces/order | spaces_reorder | OrderRequest | 204 无响应体 |
| GET | /api/spaces/{space_id}/categories | categories_list | 无请求体，查询 limit、cursor | 200 CategoryPage |
| POST | /api/spaces/{space_id}/categories | categories_create | CategoryCreate | 201 CategoryDetail；200 CategoryDetail |
| GET | /api/categories/{category_id} | categories_detail | 无请求体 | 200 CategoryDetail |
| PATCH | /api/categories/{category_id} | categories_update | CategoryPatch | 200 CategoryDetail |
| DELETE | /api/categories/{category_id} | categories_delete | 无请求体，查询 expected_updated_at | 204 无响应体 |
| GET | /api/tags | tags_list | 无请求体，查询 limit、cursor、q | 200 TagPage |
| POST | /api/tags | tags_create | NamedCreate | 201 TagDetail；200 TagDetail |
| PATCH | /api/tags/{tag_id} | tags_update | TagPatch | 200 TagDetail |
| DELETE | /api/tags/{tag_id} | tags_delete | 无请求体，查询 expected_updated_at | 204 无响应体 |
| GET | /api/content-types | content_types_list | 无请求体 | 200 ContentTypeOptions |

SpacePatch、CategoryPatch 和 TagPatch 仅修改实际提交的字段，expected_updated_at 必填，除此以外至少提交一项修改。缺省表示不变，名称和说明不接受 null，CategoryPatch 的 parent_id=null 表示移到当前空间根部。冲突返回 409 timestamp_conflict 及 current_updated_at，前端重新读取并保留本地修改。分类父子必须属于同一空间，拒绝环路和移到自身。

空间排序提交 expected_order（读取时的完整顺序）和 ordered_ids（期望完整顺序），两者必须是同一组无重复 ID。事务内锁定空间集合并比对当前顺序，存在并发新增、删除或顺序变化时返回 409 order_conflict，避免依赖集合最大更新时间导致误判。成功返回 204，随后按需重新读取空间列表。

删除空间或分类时，含正常或回收站记录、含子分类均返回 409，用户先显式处理归属。标签删除只解除标签连接并保留记录，受影响记录递增版本以防旧标签写回。分类平铺分页返回 parent_id，客户端取完所需页后组树，不能把不完整分页当完整树。内容类型为四个固定值，label_key 由前端翻译。无类型显示为未设置。

## 记录接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| POST | /api/contents | contents_create | ContentCreate | 201 ContentDetail；200 ContentDetail |
| GET | /api/contents | contents_list | 无请求体，查询 limit、cursor、space_id、category_id、tag_id、q、content_type、updated_after、updated_before、unclassified、sort | 200 ContentPage |
| GET | /api/contents/{content_id} | contents_detail | 无请求体 | 200 ContentDetail |
| PATCH | /api/contents/{content_id} | contents_update | ContentPatch | 200 ContentDetail |

所有业务操作均要求有效所有者会话。

- 新建允许空标题和未分类。不创建没有文字或附件的空记录，有文字或附件即可无标题保存。Schema 拒绝无文字且无附件的新建请求，标题不算正文。request_id 用于同所有者范围的创建幂等：首次成功返回 201，相同标识及载荷重试返回 200；载荷不同返回 409。创建摘要需基于规范化载荷计算；重试不覆盖用户后来编辑的内容。
- owner_id 只能来自有效会话，客户端不能提交或覆盖。所有读写均限制所有者，已删除记录排除在本批接口之外；不属于当前用户的详情统一返回 404。
- 正文使用 Tiptap JSON，纯文本由服务端生成。Document 根节点固定为 doc，EditorNode 约束受支持的节点类型和嵌套结构。文字节点必须含 text，文件与 HTML 展示节点必须含 attrs.attachment_id，外部嵌入必须含 HTTP(S) 的 attrs.url。服务端按受支持节点解释属性和 marks，不把它们当原始 HTML 执行。
- PATCH 必须携带 expected_version 并实际修改至少一个字段。字段缺省表示不改；content_type、space_id、category_id 可以显式 null 清空，title、body、tag_ids、attachment_ids 不接受 null。空标签数组表示清除标签。服务层必须使用 exclude_unset，不能把模型默认值误当作更新。
- 更新通过 owner_id、id、expected_version 做条件更新；版本冲突返回 409，code=version_conflict 且 current_version 为最新版本。内容、正文、纯文本、归属、标签和索引任务在同一事务内保存，成功后 version 增加并更新 updated_at。
- attachment_ids 是记录当前附件的完整 UUID 列表，新建缺省为空，更新缺省不改、空数组清除。只接受当前所有者已上传完成的附件，正文的所有文件节点引用须包含在此列表。提交新建前校验附件权限与状态；更新合并现有正文与附件后再次检查文字或附件至少有一项，禁止只清空正文或附件时绕过空记录规则。附件上传本身按附件接口独立处理。
- 无标题记录的 display_name 由服务端取正文首个有文字的行，只有附件时取文件名；title 保持用户原值。多附件时按 attachment_ids 顺序取首个文件名。列表与详情均返回 display_name。
- 归属和标签必须存在且属于当前用户。PATCH 合并已有值后重新校验空间、分类关系；不能仅靠请求字段验证最终状态。数据库复合外键作为第二层保护。
- 列表按 updated_at、id 倒序使用游标分页。游标绑定筛选条件，错误或不匹配的游标返回 422。每页默认 30、最多 100；列表不返回正文，不计算总数。编辑会改变排序，不承诺跨请求快照一致。
- 公共错误字段为 code、message、details、current_version；业务错误使用稳定 code，不依赖中文文案判断。校验响应不返回原始输入、数据库异常或凭据。

修改接口定义时同步更新 Schema、OpenAPI 操作定义、生成文件与本文规则。

## 搜索接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| GET | /api/search | search_contents | 无请求体，查询 limit、cursor、q、space_id、category_id、tag_id、content_type、updated_after、updated_before、unclassified、sort | 200 SearchPage |

私人搜索 q 必填且不能只有空白，匹配标题与正文，返回纯文本 snippet 与 matched_fields，前端转义显示。支持空间、分类、类型、标签、更新时间、未分类和排序组合。relevance 排序需要非空 q；updated_after 必须早于 updated_before。时间筛选为半开区间，按包含下界、排除上界处理。unclassified=true 表示 category_id 为空，包含无空间记录；与指定 category_id 冲突返回 422。范围始终排除回收站。

首页最近记录与双链候选复用 GET /api/contents；组合搜索使用 GET /api/search。中文分词或子串实现不改变请求结构，检索质量按 PRD 样本验收。

## 附件接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| POST | /api/attachments | attachments_upload | multipart/form-data，request_id + file | 201 AttachmentDetail；200 AttachmentDetail |
| GET | /api/attachments/{attachment_id} | attachments_detail | 无请求体 | 200 AttachmentDetail |
| DELETE | /api/attachments/{attachment_id} | attachments_delete | 无请求体 | 204 无响应体 |
| GET | /api/attachments/{attachment_id}/download | attachments_download | 无请求体 | 200 binary |
| GET | /api/attachments/{attachment_id}/embed | attachments_embed | 无请求体 | 200 EmbedView |
| GET | /api/contents/{content_id}/attachments | content_attachments_list | 无请求体，查询 limit、cursor | 200 AttachmentPage |

一次 multipart 上传一个文件，字段为 request_id 和 file。传输完成、内容校验和持久化成功后才返回 ready；格式不支持返回 415，超过上限返回 413。失败不得把不完整文件标成 ready。同 request_id 重传校验文件摘要一致，恢复或复用同一附件，不重复生成。附件字节、格式和哈希由服务端核验，原始文件名不可作为磁盘路径。

记录中的 attachment_ids 管理引用，上传完成不表示已加入记录。下载每次鉴权，回收站附件只可通过已认证所有者的恢复界面读取。删除附件仅在记录、来源原件和备份任务均无引用时执行，否则返回 409。下载不暴露 storage_key，可流式返回。网页中的图片和下载通过带 Bearer 的 fetch 取得 Blob，避免把 Access Token 放进 URL；HTML 展示通过短时隔离地址，EmbedView 返回限制、过期时间与降级原链接，地址绑定访问范围。已经撤回或删除的公开附件不得借旧展示地址继续读取。

## 来源接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| GET | /api/sources | sources_list | 无请求体，查询 limit、cursor | 200 SourcePage |
| DELETE | /api/sources/{source_id} | sources_delete | 无请求体 | 204 无响应体 |
| GET | /api/sources/{source_id} | sources_detail | 无请求体 | 200 SourceDetail |
| GET | /api/sources/{source_id}/versions | source_versions_list | 无请求体，查询 limit、cursor | 200 SourceVersionPage |
| GET | /api/source-versions/{source_version_id} | source_versions_detail | 无请求体 | 200 SourceVersionDetail |
| GET | /api/contents/{content_id}/sources | content_sources_list | 无请求体，查询 limit、cursor | 200 ContentSourcePage |
| POST | /api/contents/{content_id}/sources | content_sources_create | ContentSourceCreate | 201 ContentSourceDetail；200 ContentSourceDetail |
| DELETE | /api/contents/{content_id}/sources/{content_source_id} | content_sources_delete | 无请求体，查询 expected_version | 204 无响应体 |

来源身份和输入版本为只读原始证据；正文编辑不改写来源，变更原资料由重新导入创建版本。ContentSourceCreate 只能引用同一所有者且对应同一来源版本的解析结果，匹配 expected_version 后原子建立引用、递增记录版本并返回 content_version。解除引用保留来源原件，成功后客户端重新读取记录版本。

删除来源前检查全部记录引用，仍被记录引用或有处理中任务时返回 409。确认后按依赖逆序清理此来源的版本、解析结果、原件及对应导入项，保留批次中的其他项目并重新计算统计；其他引用中的附件继续保留。删除提示须列出受影响的来源、文件和导入证据范围。SourceVersionDetail 的原件通过附件下载读取。角色、时间与会话分支通过原始会话接口回看，不把 AI 回答标记成用户表达。

## 导入接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| POST | /api/import-previews | import_previews_create | ImportPreviewRequest | 202 ImportPreviewDetail；200 ImportPreviewDetail |
| GET | /api/import-previews/{preview_id} | import_previews_detail | 无请求体 | 200 ImportPreviewDetail |
| GET | /api/import-previews/{preview_id}/items | import_candidates_list | 无请求体，查询 limit、cursor | 200 ImportCandidatePage |
| POST | /api/imports | imports_create | ImportCreate | 202 ImportJobDetail；200 ImportJobDetail |
| GET | /api/imports | imports_list | 无请求体，查询 limit、cursor | 200 ImportJobPage |
| GET | /api/imports/{job_id} | imports_detail | 无请求体 | 200 ImportJobDetail |
| GET | /api/imports/{job_id}/items | import_items_list | 无请求体，查询 limit、cursor | 200 ImportItemPage |
| POST | /api/imports/{job_id}/retries | imports_retry | RetryImportRequest | 202 ImportJobDetail；200 ImportJobDetail |
| POST | /api/reparses | reparses_create | ReparseRequest | 202 ProcessingDetail；200 ProcessingDetail |
| GET | /api/reparses/{run_id} | reparses_detail | 无请求体 | 200 ProcessingDetail |
| GET | /api/normalized-documents/{document_id} | normalized_documents_detail | 无请求体 | 200 NormalizedDocumentDetail |
| POST | /api/contents/{content_id}/parsed-updates | parsed_updates_apply | ApplyParsedRequest | 200 ContentDetail |
| GET | /api/source-versions/{source_version_id}/conversation | conversations_detail | 无请求体 | 200 ConversationDetail |
| GET | /api/conversations/{conversation_id}/messages | conversation_messages_list | 无请求体，查询 limit、cursor | 200 ConversationMessagePage |

先上传原文件，再提交 ImportPreviewRequest；URL 导入直接提交链接，文件与 URL 不得混用。预览只生成临时处理结果，不创建正式记录；上传成功与解析成功分别反馈。预览就绪后分页读取候选，会话 item_key 保持稳定。所有者选择 selected_item_keys，再以 preview_id 和 preview_version 创建导入批次；预览过期返回 409，必须重新预览。只导入选中的项目。

URL 抓取禁止访问内网、元数据服务及重定向后的私有地址，限制大小、超时及递归资源。提取失败仍保留原始 URL，可结合 personal_summary 创建链接记录；没有摘要时生成包含原始 URL 的正文，不让空记录校验阻断链接保存。

ImportJob 统计与单项状态一致，partial 表示部分成功。重试请求指定当前批次的失败或部分成功 item_ids，成功项不重复创建，处理中项目不能重复领取。每次重试和重解析保留旧尝试、原件与来源版本。NormalizedDocumentDetail 为候选结果，只有调用 parsed_updates_apply、校验 expected_version 且确认来源兼容后才原子应用到已有记录。接受结果仍只保存私人修改，不能触发发布。

消息按 sequence、id 升序分页，保留 role 原值、父消息 external ID、时间及附件引用；附件无法解析时反馈警告，原始导出文件仍可下载。原文不提供编辑接口。批次详情不包含所有消息，避免长对话一次性返回。

## 内容关联接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| GET | /api/contents/{content_id}/relations | relations_list | 无请求体，查询 limit、cursor、direction | 200 RelationPage |
| POST | /api/contents/{content_id}/relations | relations_create | RelationCreate | 201 RelationDetail；200 RelationDetail |
| DELETE | /api/relations/{relation_id} | relations_delete | 无请求体 | 204 无响应体 |

related_to 按两端 ID 规范化存储，作为双向关系展示；prerequisite、application、contrast 保留起点和目标。拒绝自关联、跨所有者关联和已删除目标。相同两端、类型的关系不能重复，幂等请求返回已有结果。GET 的 direction 默认 all；incoming 与 outgoing 对双向相关关系均可见。删除只解除关系，两端记录保留。

正文中的 [[链接]] 以稳定 ID 存储引用，私人搜索提供选择候选。原文引用与关系表在保存服务中协调，不能仅凭标题重建关系。关联不隐式改变目录、类型或发布状态。

## 回收站接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| DELETE | /api/contents/{content_id} | contents_delete | 无请求体，查询 expected_version | 204 无响应体 |
| GET | /api/trash | trash_list | 无请求体，查询 limit、cursor | 200 TrashPage |
| GET | /api/trash/{content_id} | trash_detail | 无请求体 | 200 ContentDetail |
| DELETE | /api/trash/{content_id} | trash_purge | 无请求体，查询 expected_version | 204 无响应体 |
| POST | /api/trash/{content_id}/restore | trash_restore | VersionRequest | 200 ContentRestoreResult |

普通删除匹配记录版本后设置 deleted_at、递增版本，并同时停止公开。回收站按 deleted_at、id 倒序分页。所有者可读取回收站详情用于恢复和永久删除，普通列表与搜索不返回这些记录。

恢复只针对回收站记录，匹配 expected_version，保留有效位置，位置失效时清空无效归属。ContentRestoreResult 返回恢复后的记录、location_changed 和私人发布状态。永久删除只接受已在回收站的记录，清理成员、关联、标签及正文；来源与其他记录共享的原件继续保留。删除前端必须提示影响并确认。V1.0 不自动清空，也不通过单条接口隐式批量删除。

## 思考脉络接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| GET | /api/threads | threads_list | 无请求体，查询 limit、cursor | 200 ThreadPage |
| POST | /api/threads | threads_create | ThreadCreate | 201 ThreadDetail；200 ThreadDetail |
| GET | /api/threads/{thread_id} | threads_detail | 无请求体 | 200 ThreadDetail |
| PATCH | /api/threads/{thread_id} | threads_update | ThreadPatch | 200 ThreadDetail |
| DELETE | /api/threads/{thread_id} | threads_delete | 无请求体，查询 expected_version | 204 无响应体 |
| GET | /api/threads/{thread_id}/timeline | threads_timeline | 无请求体，查询 limit、cursor | 200 ThreadTimeline |
| PUT | /api/threads/{thread_id}/members/{content_id} | threads_member_add | VersionRequest | 200 ThreadDetail |
| DELETE | /api/threads/{thread_id}/members/{content_id} | threads_member_remove | 无请求体，查询 expected_version | 200 ThreadDetail |

主题名不能只含空白。创建的 request_id 在所有者范围内去重，不同载荷复用返回 409。列表按 updated_at、id 倒序，时间线按记录 created_at、id 升序，分页默认 30、最多 100，游标绑定主题与排序条件。时间线返回记录摘要、来源发生时间 original_occurred_at 和 imported_at，未知时间为 null，不把导入时间当成发生时间。

主题与成员记录均限制当前所有者。成员唯一键为主题与记录的组合。重复加入或移出先检查目标状态，已达成时返回当前主题而不增加版本；实际修改须匹配 expected_version，并在同一事务内修改关系、递增主题版本。删除主题只删除主题和成员关系，保留记录。回收站记录不返回正文摘要，恢复后恢复正常展示，永久删除时清理成员引用。

## 发布接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| GET | /api/contents/{content_id}/publication | publications_detail | 无请求体 | 200 PublicationDetail |
| POST | /api/contents/{content_id}/publication | publications_publish | PublicationRequest | 200 PublicationDetail |
| POST | /api/contents/{content_id}/publication/preview | publications_preview | PublicationPreviewRequest | 200 PublicationPreview |
| POST | /api/contents/{content_id}/publication/withdraw | publications_withdraw | WithdrawRequest | 200 PublicationDetail |

PublicationPreviewRequest 包含 expected_version 和 public_attachment_ids，不要求幂等标识。只读预览返回当前 publication_version。正式发布的 PublicationRequest 另包含 request_id 和 expected_publication_version，发布时同时校验记录和发布状态两个版本。正文版本冲突返回 version_conflict，发布状态冲突返回 publication_version_conflict，current_version 按对应错误返回当前版本值。预览及发布均针对已保存的 expected_version；当前记录版本不匹配时返回 409。预览只读，发布时再次检查标题、正文、所有者、附件范围及记录版本，不能只依赖客户端曾打开预览。缺少标题或可展示正文返回 422。public_attachment_ids 必须是本条记录附件的子集，外部文件与未选定的附件不可匿名读取。

request_id 用于发布重试幂等，先检查同所有者、同记录的历史请求结果；同载荷重试返回原结果，不再次发布，载荷不同返回 409。发布成功时原子保存公开版本的标题、正文、关联展示数据与明确选中的附件范围。自动保存只更新私人记录，公开查询始终读取上次成功发布版本。发布失败时保留原公开版本和私人修改。

PublicationDetail 返回 publication_version、published_content_version、has_unpublished_changes、public_url 与发布时间。publication_version 在首次发布、更新发布和撤回时单调递增，初始未发布时为 0。从未发布时 published_content_version、URL 和发布时间均为 null；有私人新版本时 has_unpublished_changes 为 true。撤回使用 expected_publication_version，避免同一正文版本重新发布或修改附件范围后被旧请求撤回。版本不匹配返回 409；同一撤回请求的重复调用须识别上次已撤回版本且期间未重新发布，才可幂等成功。撤回及删除清理匿名入口、公开搜索、缓存与附件访问。回收站恢复后保持私有。重新发布是否沿用原公开地址仍按 PRD 待定项处理，客户端只使用服务端返回的 public_url。

## 导出、备份与恢复接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| POST | /api/exports | exports_create | ExportCreate | 202 JobDetail；200 JobDetail |
| GET | /api/exports/{job_id} | exports_detail | 无请求体 | 200 JobDetail |
| GET | /api/exports/{job_id}/download | exports_download | 无请求体 | 200 binary |
| POST | /api/backups | backups_create | RequestIdentity | 202 JobDetail；200 JobDetail |
| GET | /api/backups | backups_list | 无请求体，查询 limit、cursor | 200 JobPage |
| GET | /api/backups/{job_id} | backups_detail | 无请求体 | 200 JobDetail |
| GET | /api/backups/{job_id}/download | backups_download | 无请求体 | 200 binary |
| POST | /api/backup-inspections | backup_inspections_create | BackupInspectionRequest | 200 BackupInspection |
| POST | /api/restores | restores_create | RestoreCreate | 202 JobDetail；200 JobDetail |
| GET | /api/restores/{job_id} | restores_detail | 无请求体 | 200 JobDetail |

Markdown 导出以非空 content_ids 选择单条或多条记录，服务端核验所有权并固定本次内容版本。include_metadata 控制来源、标签和组织属性。导出中不支持的节点进入 warnings，不能静默丢失。任务成功后下载文件，未完成返回 409；同 request_id 不重新生成另一份结果。

完整备份包含正文、空间分类、标签、关系、人工脉络与成员、来源链、原件和附件、删除与发布状态以及已发布内容版本。会话令牌和账号密码不进入备份。数据库与文件使用一致性快照及清单校验，文件共享引用保持一致。备份格式版本由结果清单给出。

恢复先上传备份，再执行 backup-inspections 检查格式、校验和、文件完整性和数量；响应含 inspection_id 对应的 id、expires_at 和 workspace_empty。用户确认后提交 RestoreCreate 的 inspection_id 与 expected_checksum。创建恢复任务时再次检查原件摘要与空工作区并锁定恢复范围。导入的临时备份文件、当前账号和任务本身不计作已有笔记数据。

恢复固定原 ID 并将归属绑定当前所有者，非空工作区返回 409。失败时回滚或隔离暂存结果，未成功的工作区不可被误认为完整恢复。恢复写入期间禁止其他业务写入，以 409 workspace_restoring 反馈。任务结果单独可查。全部备份及导出下载仅限所有者，每次访问重新检查权限。恢复后所有记录保持私有；备份中的历史公开版本及元数据可保留作历史，但不得自动启用公开路由、搜索、缓存或附件。重新公开必须由所有者主动发布。

## Site 公开接口

| 方法 | 路径 | operationId | 请求 | 成功响应 |
| --- | --- | --- | --- | --- |
| GET | /api/public/site | public_site_detail | 无请求体 | 200 PublicSiteDetail |
| GET | /api/public/contents | public_contents_list | 无请求体，查询 limit、cursor、q、category_key、tag_key | 200 PublicContentPage |
| GET | /api/public/contents/{slug} | public_contents_detail | 无请求体 | 200 PublicContentDetail |
| GET | /api/public/categories | public_categories_list | 无请求体，查询 limit、cursor | 200 PublicLinkPage |
| GET | /api/public/tags | public_tags_list | 无请求体，查询 limit、cursor | 200 PublicLinkPage |
| GET | /api/public/contents/{slug}/attachments/{attachment_key} | public_attachments_download | 无请求体 | 200 binary |
| GET | /api/public/contents/{slug}/embeds/{attachment_key} | public_attachments_embed | 无请求体 | 200 EmbedView |
| GET | /api/public/sitemap | public_sitemap_list | 无请求体，查询 limit、cursor | 200 SitemapPage |

Site 首页和知识列表复用公开内容列表，默认按 published_at、slug 倒序；q 提供公开搜索，category_key 和 tag_key 为公开筛选标识。列表、分类、标签和站点地图仅包含当前有效发布数据。分类名与标签名必须来自已发布版本的允许范围，不能从私人记录推导额外信息。

公开详情使用 PublicContentDetail 和 PublicDocument，按字段白名单构建。正文中的私人 attachment_id 改为选定公开文件的 attachment_key，关系目标改为公开 slug。未公开目标的标题、摘要、UUID 和来源元数据不得出现在响应中。公开文档属性禁止透传任意私人 JSON。

附件路径同时包含文章 slug 和附件 key，每次校验父记录仍已发布且附件包含在当前发布版本中。撤回后立即失效，隔离预览地址也不得绕过检查。静态缓存、站点地图和反向关联必须随撤回或删除失效。Site 可将 sitemap 数据转成 XML，文章 SEO 从公开标题和摘要生成。

## HTML 与文件节点

正文保存文件附件引用，不在节点中保存可直接执行的 HTML 源码。HTML 文件通过隔离展示服务读取，导入为正文时执行清洗和转换。外部嵌入链接保存为 externalEmbed 节点，服务端及客户端限制协议与可用来源。节点属性的 URL 或文件引用不代替访问权限；公开预览和发布只暴露选定范围。HTML 的脚本执行、外部资源加载及允许来源属于尚未确定的产品与安全参数。

## 数据结构

字段表与 OpenAPI 对应。必填表示必须提交或返回，类型含 null 表示允许空值。PATCH 默认值仅用于解析，实际更新使用显式提交的字段。

### AccountDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| username | string | 是 | — | 登录账号名 |
| display_name | string | 是 | — | 显示名称 |

### AccountPatch

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| display_name | string | 是 | — | 显示名称 |

### ApplyParsedRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| normalized_document_id | uuid | 是 | — | 规范解析结果ID |
| expected_version | integer | 是 | — | 客户端读取的记录或主题版本 |

### AttachmentDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| original_name | string | 是 | — | 原始文件名 |
| mime_type | string | 是 | — | 文件媒体类型 |
| byte_size | integer | 是 | — | 文件字节数 |
| sha256 | string / null | 是 | — | 文件 SHA-256 摘要 |
| status | pending、ready、failed | 是 | — | 资源或任务状态 |
| created_at | date-time | 是 | — | 创建时间 |

### AttachmentPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | AttachmentDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### BackupInspection

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| attachment_id | uuid | 是 | — | 附件ID |
| format_version | string | 是 | — | 备份格式版本 |
| checksum | string | 是 | — | 原件校验摘要 |
| content_count | integer | 是 | — | 记录数量 |
| attachment_count | integer | 是 | — | 附件数量 |
| thread_count | integer | 是 | — | 思考主题数量 |
| compatible | boolean | 是 | — | 备份格式是否兼容 |
| workspace_empty | boolean | 是 | — | 工作区是否满足空白恢复条件 |
| warnings | string[] | 是 | — | 转换或处理警告 |
| expires_at | date-time | 是 | — | 会话、预览或临时地址的失效时间 |

### BackupInspectionRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| attachment_id | uuid | 是 | — | 附件ID |

### CategoryCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| name | string | 是 | — | 名称 |
| parent_id | uuid / null | 否 | None | 父分类ID，空值表示根分类 |

### CategoryDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| space_id | uuid | 是 | — | 空间ID |
| parent_id | uuid / null | 是 | — | 父分类ID，空值表示根分类 |
| name | string | 是 | — | 名称 |
| sort_order | integer | 是 | — | 同级排序值 |
| updated_at | date-time | 是 | — | 最近更新时间 |

### CategoryPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | CategoryDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### CategoryPatch

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| name | string | 否 | '' | 名称 |
| expected_updated_at | date-time | 是 | — | 客户端读取的更新时间，用于并发校验 |
| parent_id | uuid / null | 否 | None | 父分类ID，空值表示根分类 |
| sort_order | integer | 否 | 0 | 同级排序值 |

### ContentCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| title | string | 否 | '' | 标题原值 |
| body | Document | 否 | — | 结构化正文 |
| content_type | knowledge、experience、memory_note、thought / null | 否 | None | 内容类型代码 |
| space_id | uuid / null | 否 | None | 空间ID |
| category_id | uuid / null | 否 | None | 分类ID |
| tag_ids | uuid[] | 否 | — | 记录标签ID完整列表 |
| attachment_ids | uuid[] | 否 | — | 附件ID完整列表 |

### ContentDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| title | string | 是 | — | 标题原值 |
| content_type | knowledge、experience、memory_note、thought / null | 是 | — | 内容类型代码 |
| space_id | uuid / null | 是 | — | 空间ID |
| category_id | uuid / null | 是 | — | 分类ID |
| display_name | string | 是 | — | 显示名称 |
| version | integer | 是 | — | 资源并发版本号 |
| created_at | date-time | 是 | — | 创建时间 |
| updated_at | date-time | 是 | — | 最近更新时间 |
| body | Document | 是 | — | 结构化正文 |
| tag_ids | uuid[] | 是 | — | 记录标签ID完整列表 |
| attachment_ids | uuid[] | 是 | — | 附件ID完整列表 |

### ContentPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ContentSummary[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### ContentPatch

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| expected_version | integer | 是 | — | 客户端读取的记录或主题版本 |
| title | string | 否 | '' | 标题原值 |
| body | Document | 否 | — | 结构化正文 |
| content_type | knowledge、experience、memory_note、thought / null | 否 | None | 内容类型代码 |
| space_id | uuid / null | 否 | None | 空间ID |
| category_id | uuid / null | 否 | None | 分类ID |
| tag_ids | uuid[] | 否 | — | 记录标签ID完整列表 |
| attachment_ids | uuid[] | 否 | — | 附件ID完整列表 |

### ContentRestoreResult

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| content | ContentDetail | 是 | — | 记录摘要或正文子节点，按所属模型解释 |
| location_changed | boolean | 是 | — | 恢复时是否调整了失效位置 |
| publication_status | draft、withdrawn | 是 | — | 恢复后的私人发布状态 |

### ContentSourceCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| source_version_id | uuid | 是 | — | 来源版本ID |
| normalized_document_id | uuid / null | 否 | None | 规范解析结果ID |
| expected_version | integer | 是 | — | 客户端读取的记录或主题版本 |

### ContentSourceDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| content_id | uuid | 是 | — | 记录ID |
| source_version_id | uuid | 是 | — | 来源版本ID |
| normalized_document_id | uuid / null | 是 | — | 规范解析结果ID |
| content_version | integer | 是 | — | 记录当前版本 |

### ContentSourcePage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ContentSourceDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### ContentSummary

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| title | string | 是 | — | 标题原值 |
| content_type | knowledge、experience、memory_note、thought / null | 是 | — | 内容类型代码 |
| space_id | uuid / null | 是 | — | 空间ID |
| category_id | uuid / null | 是 | — | 分类ID |
| display_name | string | 是 | — | 显示名称 |
| version | integer | 是 | — | 资源并发版本号 |
| created_at | date-time | 是 | — | 创建时间 |
| updated_at | date-time | 是 | — | 最近更新时间 |

### ContentTypeOption

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| value | knowledge、experience、memory_note、thought | 是 | — | 固定选项代码 |
| label_key | string | 是 | — | 前端翻译键 |

### ContentTypeOptions

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ContentTypeOption[] | 是 | — | 本页条目 |

### ConversationDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| source_version_id | uuid | 是 | — | 来源版本ID |
| platform | string | 是 | — | 来源平台 |
| external_id | string / null | 是 | — | 来源平台外部标识 |
| title | string | 是 | — | 标题原值 |
| occurred_at | date-time / null | 是 | — | 原始事件或消息时间 |

### ConversationMessage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| sequence | integer | 是 | — | 原会话中的消息顺序 |
| external_message_id | string / null | 是 | — | 来源平台消息标识 |
| parent_external_id | string / null | 是 | — | 来源平台父消息标识 |
| role | string | 是 | — | 原平台消息角色 |
| text | string | 是 | — | 原始文字 |
| attachment_ids | uuid[] | 是 | — | 附件ID完整列表 |
| occurred_at | date-time / null | 是 | — | 原始事件或消息时间 |

### ConversationMessagePage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ConversationMessage[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### Document

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| type | doc | 否 | 'doc' | 正文节点或格式标记类型 |
| content | EditorNode[] | 否 | — | 记录摘要或正文子节点，按所属模型解释 |

### EditorNode

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| type | paragraph、heading、text、bulletList、orderedList、listItem、blockquote、codeBlock、hardBreak、horizontalRule、table、tableRow、tableCell、tableHeader、image、file、htmlEmbed、externalEmbed | 是 | — | 正文节点或格式标记类型 |
| text | string / null | 否 | None | 原始文字 |
| attrs | object | 否 | — | 节点属性 |
| marks | object[] | 否 | — | 文本格式标记 |
| content | EditorNode[] | 否 | — | 记录摘要或正文子节点，按所属模型解释 |

### EmbedView

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| url | uri | 是 | — | 来源或展示链接 |
| sandbox | string | 是 | — | HTML 展示容器的隔离限制 |
| expires_at | date-time | 是 | — | 会话、预览或临时地址的失效时间 |
| fallback_url | uri | 是 | — | 展示失败时的原链接 |

### ErrorDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| field | string | 是 | — | 错误字段路径 |
| message | string | 是 | — | 供用户阅读的错误提示 |

### ErrorResponse

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| code | string | 是 | — | 稳定业务错误码 |
| message | string | 是 | — | 供用户阅读的错误提示 |
| details | ErrorDetail[] | 否 | [] | 字段错误详情 |
| current_version | integer / null | 否 | None | 冲突时服务端当前版本 |
| current_updated_at | date-time / null | 否 | None | 时间戳冲突时的服务端当前更新时间 |

### ExportCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| content_ids | uuid[] | 是 | — | 选择的记录ID列表 |
| include_metadata | boolean | 否 | True | 是否导出组织及来源元数据 |

### ImportCandidate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| item_key | string | 是 | — | 批次内稳定项目标识 |
| title | string | 是 | — | 标题原值 |
| preview_text | string | 是 | — | 供选择的原文摘要 |
| message_count | integer / null | 是 | — | 会话消息数量 |
| warnings | string[] | 是 | — | 转换或处理警告 |
| duplicate_content_id | uuid / null | 是 | — | 检测到的已有重复记录ID |

### ImportCandidatePage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ImportCandidate[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### ImportCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| preview_id | uuid | 是 | — | 导入预览ID |
| preview_version | integer | 是 | — | 用户选择时的预览版本 |
| selected_item_keys | string[] | 是 | — | 用户选定的候选项目标识 |

### ImportItemDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| job_id | uuid | 是 | — | 任务或批次ID |
| source_version_id | uuid | 是 | — | 来源版本ID |
| item_key | string | 是 | — | 批次内稳定项目标识 |
| status | queued、processing、success、partial、failed、skipped | 是 | — | 资源或任务状态 |
| content_id | uuid / null | 是 | — | 记录ID |
| error_code | string / null | 是 | — | 处理错误代码 |
| error_detail | string / null | 是 | — | 处理错误说明 |
| normalized_document_id | uuid / null | 是 | — | 规范解析结果ID |

### ImportItemPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ImportItemDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### ImportJobDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| status | queued、processing、success、partial、failed | 是 | — | 资源或任务状态 |
| total | integer | 是 | — | 批次项目总数 |
| succeeded | integer | 是 | — | 成功项目数 |
| failed | integer | 是 | — | 失败项目数 |
| skipped | integer | 是 | — | 跳过项目数 |
| created_at | date-time | 是 | — | 创建时间 |
| updated_at | date-time | 是 | — | 最近更新时间 |

### ImportJobPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ImportJobDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### ImportPreviewDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| status | queued、processing、ready、failed | 是 | — | 资源或任务状态 |
| version | integer | 是 | — | 资源并发版本号 |
| error_code | string / null | 是 | — | 处理错误代码 |
| expires_at | date-time | 是 | — | 会话、预览或临时地址的失效时间 |

### ImportPreviewRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| kind | files、url、chatgpt | 是 | — | 来源或任务类型 |
| attachment_ids | uuid[] | 否 | — | 附件ID完整列表 |
| url | uri / null | 否 | None | 来源或展示链接 |
| personal_summary | string | 否 | '' | 网页保存时补充的个人摘要 |

### JobDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| kind | markdown_export、backup、restore | 是 | — | 来源或任务类型 |
| status | queued、processing、success、failed | 是 | — | 资源或任务状态 |
| error_code | string / null | 是 | — | 处理错误代码 |
| error_detail | string / null | 是 | — | 处理错误说明 |
| warnings | string[] | 是 | — | 转换或处理警告 |
| created_at | date-time | 是 | — | 创建时间 |
| updated_at | date-time | 是 | — | 最近更新时间 |

### JobPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | JobDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### LoginRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| username | string | 是 | — | 登录账号名 |
| password | password | 是 | — | 登录密码，仅请求使用 |

### NamedCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| name | string | 是 | — | 名称 |

### NamedPatch

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| name | string | 否 | '' | 名称 |
| expected_updated_at | date-time | 是 | — | 客户端读取的更新时间，用于并发校验 |

### NormalizedDocumentDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| source_version_id | uuid | 是 | — | 来源版本ID |
| body | Document | 是 | — | 结构化正文 |
| plain_text | string | 是 | — | 正文纯文本 |
| warnings | string[] | 是 | — | 转换或处理警告 |

### OrderRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| ordered_ids | uuid[] | 是 | — | 按目标顺序排列的完整ID列表 |
| expected_order | uuid[] | 是 | — | 读取时的完整空间顺序 |

### PasswordChange

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| current_password | password | 是 | — | 当前密码，仅请求使用 |
| new_password | password | 是 | — | 新密码，仅请求使用 |

### ProcessingDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| source_version_id | uuid | 是 | — | 来源版本ID |
| status | queued、processing、success、partial、failed | 是 | — | 资源或任务状态 |
| normalized_document_id | uuid / null | 是 | — | 规范解析结果ID |
| error_code | string / null | 是 | — | 处理错误代码 |
| warnings | string[] | 是 | — | 转换或处理警告 |

### PublicContentDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| slug | string | 是 | — | 稳定公开路径标识 |
| title | string | 是 | — | 标题原值 |
| excerpt | string | 是 | — | 公开摘要 |
| published_at | date-time | 是 | — | 首次成功发布时间 |
| updated_at | date-time | 是 | — | 最近更新时间 |
| body | PublicDocument | 是 | — | 结构化正文 |
| relations | PublicRelation[] | 是 | — | 可公开的关系列表 |
| attachment_keys | string[] | 是 | — | 公开附件标识列表 |
| tags | PublicLink[] | 是 | — | 公开标签列表 |
| category | PublicLink / null | 是 | — | 公开分类 |

### PublicContentPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | PublicContentSummary[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### PublicContentSummary

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| slug | string | 是 | — | 稳定公开路径标识 |
| title | string | 是 | — | 标题原值 |
| excerpt | string | 是 | — | 公开摘要 |
| published_at | date-time | 是 | — | 首次成功发布时间 |
| updated_at | date-time | 是 | — | 最近更新时间 |

### PublicDocument

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| type | doc | 否 | 'doc' | 正文节点或格式标记类型 |
| content | PublicEditorNode[] | 是 | — | 记录摘要或正文子节点，按所属模型解释 |

### PublicEditorNode

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| type | paragraph、heading、text、bulletList、orderedList、listItem、blockquote、codeBlock、hardBreak、horizontalRule、table、tableRow、tableCell、tableHeader、image、file、htmlEmbed、externalEmbed | 是 | — | 正文节点或格式标记类型 |
| text | string / null | 否 | None | 原始文字 |
| attrs | PublicNodeAttributes | 否 | — | 节点属性 |
| marks | PublicMark[] | 否 | — | 文本格式标记 |
| content | PublicEditorNode[] | 否 | — | 记录摘要或正文子节点，按所属模型解释 |

### PublicLink

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| name | string | 是 | — | 名称 |
| key | string | 是 | — | 公开筛选标识 |

### PublicLinkPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | PublicLink[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### PublicMark

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| type | bold、italic、strike、code、link、underline | 是 | — | 正文节点或格式标记类型 |
| attrs | PublicNodeAttributes | 否 | — | 节点属性 |

### PublicNodeAttributes

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| attachment_key | string / null | 否 | None | 公开附件标识 |
| url | string / null | 否 | None | 来源或展示链接 |
| level | integer / null | 否 | None | 标题层级 |
| language | string / null | 否 | None | 代码语言 |
| start | integer / null | 否 | None | 有序列表起始编号 |
| colspan | integer / null | 否 | None | 合并列数 |
| rowspan | integer / null | 否 | None | 合并行数 |
| colwidth | integer[] / null | 否 | None | 列宽列表 |
| align | string / null | 否 | None | 对齐方式 |
| alt | string / null | 否 | None | 图片替代文字 |
| title | string / null | 否 | None | 标题原值 |
| href | string / null | 否 | None | 链接目标 |

### PublicRelation

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| title | string | 是 | — | 标题原值 |
| slug | string | 是 | — | 稳定公开路径标识 |
| relation_type | string | 是 | — | 关系类型代码 |

### PublicSiteDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| display_name | string | 是 | — | 显示名称 |
| content_base_path | /knowledge | 否 | '/knowledge' | 公开内容路由前缀 |

### PublicationDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| content_id | uuid | 是 | — | 记录ID |
| status | draft、published、withdrawn | 是 | — | 资源或任务状态 |
| published_content_version | integer / null | 是 | — | 当前公开版本对应的记录版本 |
| publication_version | integer | 是 | — | 发布状态并发版本号 |
| has_unpublished_changes | boolean | 是 | — | 是否有尚未发布的私人修改 |
| public_url | string / null | 是 | — | 服务端返回的公开地址 |
| published_at | date-time / null | 是 | — | 首次成功发布时间 |
| updated_at | date-time / null | 是 | — | 最近更新时间 |

### PublicationPreview

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| content_id | uuid | 是 | — | 记录ID |
| content_version | integer | 是 | — | 记录当前版本 |
| publication_version | integer | 是 | — | 发布状态并发版本号 |
| title | string | 是 | — | 标题原值 |
| body | Document | 是 | — | 结构化正文 |
| public_attachment_ids | uuid[] | 是 | — | 明确选择公开的附件ID列表 |

### PublicationPreviewRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| expected_version | integer | 是 | — | 客户端读取的记录或主题版本 |
| public_attachment_ids | uuid[] | 否 | — | 明确选择公开的附件ID列表 |

### PublicationRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| expected_version | integer | 是 | — | 客户端读取的记录或主题版本 |
| public_attachment_ids | uuid[] | 否 | — | 明确选择公开的附件ID列表 |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| expected_publication_version | integer | 是 | — | 预览时读取的发布状态版本号 |

### RelationCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| target_content_id | uuid | 是 | — | 待关联目标记录ID |
| relation_type | related_to、prerequisite、application、contrast | 是 | — | 关系类型代码 |
| description | string | 否 | '' | 说明 |

### RelationDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| from_content_id | uuid | 是 | — | 关系起点记录ID |
| to_content_id | uuid | 是 | — | 关系终点记录ID |
| relation_type | related_to、prerequisite、application、contrast | 是 | — | 关系类型代码 |
| description | string | 是 | — | 说明 |
| other | ContentSummary | 是 | — | 关系另一端的记录摘要 |
| direction | incoming、outgoing、bidirectional | 是 | — | 相对当前记录的关联方向 |

### RelationPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | RelationDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### ReparseRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| source_version_id | uuid | 是 | — | 来源版本ID |

### RequestIdentity

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |

### RestoreCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| inspection_id | uuid | 是 | — | 备份检查结果ID |
| expected_checksum | string | 是 | — | 用户预览并确认的备份摘要 |

### RetryImportRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| item_ids | uuid[] | 是 | — | 需要重试的导入项ID列表 |

### SearchHit

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| content | ContentSummary | 是 | — | 记录摘要或正文子节点，按所属模型解释 |
| snippet | string | 是 | — | 匹配内容的纯文本摘要 |
| matched_fields | title、body[] | 是 | — | 匹配的标题或正文字段 |

### SearchPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | SearchHit[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### SessionDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| account | AccountDetail | 是 | — | 当前所有者资料 |
| expires_at | date-time | 是 | — | 会话、预览或临时地址的失效时间 |
| access_token | string | 是 | — | 仅当前客户端内存持有的 JWT 访问令牌 |
| token_type | Bearer | 否 | 'Bearer' | Authorization 凭据类型 |
| access_expires_in | integer | 是 | — | 访问令牌剩余有效秒数 |

### SitemapEntry

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| path | string | 是 | — | 公开页面相对路径 |
| last_modified_at | date-time | 是 | — | 公开页面最后修改时间 |

### SitemapPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | SitemapEntry[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### SourceDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| kind | manual、file、url、chatgpt、other | 是 | — | 来源或任务类型 |
| platform | string / null | 是 | — | 来源平台 |
| external_id | string / null | 是 | — | 来源平台外部标识 |
| external_url | string / null | 是 | — | 来源原始链接 |
| created_at | date-time | 是 | — | 创建时间 |

### SourcePage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | SourceDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### SourceVersionDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| source_id | uuid | 是 | — | 来源身份ID |
| revision | integer | 是 | — | 来源输入版本号 |
| original_created_at | date-time / null | 是 | — | 来源原始创建时间 |
| original_updated_at | date-time / null | 是 | — | 来源原始更新时间 |
| captured_at | date-time | 是 | — | 原件采集时间 |
| raw_attachment_ids | uuid[] | 是 | — | 原始资料附件ID列表 |

### SourceVersionPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | SourceVersionDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### SpaceCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| name | string | 是 | — | 名称 |
| description | string | 否 | '' | 说明 |

### SpaceDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| name | string | 是 | — | 名称 |
| description | string | 是 | — | 说明 |
| sort_order | integer | 是 | — | 同级排序值 |
| content_count | integer | 是 | — | 记录数量 |
| category_count | integer | 是 | — | 分类数量 |
| updated_at | date-time | 是 | — | 最近更新时间 |

### SpacePage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | SpaceDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### SpacePatch

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| name | string | 否 | '' | 名称 |
| expected_updated_at | date-time | 是 | — | 客户端读取的更新时间，用于并发校验 |
| description | string | 否 | '' | 说明 |

### TagDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| name | string | 是 | — | 名称 |
| updated_at | date-time | 是 | — | 最近更新时间 |

### TagPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | TagDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### TagPatch

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| name | string | 否 | '' | 名称 |
| expected_updated_at | date-time | 是 | — | 客户端读取的更新时间，用于并发校验 |

### ThreadCreate

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| request_id | uuid | 是 | — | 客户端生成的幂等请求标识 |
| name | string | 是 | — | 名称 |

### ThreadDetail

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | uuid | 是 | — | 当前资源ID |
| name | string | 是 | — | 名称 |
| version | integer | 是 | — | 资源并发版本号 |
| created_at | date-time | 是 | — | 创建时间 |
| updated_at | date-time | 是 | — | 最近更新时间 |

### ThreadPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ThreadDetail[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### ThreadPatch

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| expected_version | integer | 是 | — | 客户端读取的记录或主题版本 |
| name | string | 是 | — | 名称 |

### ThreadTimeline

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | ThreadTimelineItem[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### ThreadTimelineItem

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| content | ContentSummary | 是 | — | 记录摘要或正文子节点，按所属模型解释 |
| original_occurred_at | date-time / null | 是 | — | 来源发生时间 |
| imported_at | date-time / null | 是 | — | 导入时间 |

### TrashItem

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| content | ContentSummary | 是 | — | 记录摘要或正文子节点，按所属模型解释 |
| deleted_at | date-time | 是 | — | 移入回收站的时间 |

### TrashPage

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | TrashItem[] | 是 | — | 本页条目 |
| next_cursor | string / null | 是 | — | 下一页游标，无下一页时为空 |

### VersionRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| expected_version | integer | 是 | — | 客户端读取的记录或主题版本 |

### WithdrawRequest

| 字段 | 类型 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| expected_publication_version | integer | 是 | — | 预览时读取的发布状态版本号 |

## 尚需确定的参数

- 认证采用双令牌方案；Access Token 和刷新会话的有效期、限流阈值与密码策略参数仍需确定。
- 请求与文件上限、格式白名单、HTML 脚本和外部资源权限、外部嵌入来源。
- 备份包内部清单及版本兼容、ChatGPT 实际导出样本与中文检索实现。
- 重新发布是否沿用原公开地址。

上述事项影响配置或具体安全行为；本文已定义对应业务的输入、输出、权限和操作流程。确定后同步相应 Schema 与操作说明。
