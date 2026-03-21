# RAG 专项整改清单

更新时间：2026-03-22

## 当前结论

RAG 基础入库链路已经从 demo 外壳推进到“可解析、可切块、可入库、可失败兜底、可测试”的阶段；检索与聊天链路也已经进入“可结构化、可预处理、可接 reranker、可记录观测元数据、可做最小离线评测”的阶段。当前剩余的主要问题，不再是主链路缺失，而是生产级能力还不够深，例如真实 embedding 服务、细粒度业务 filter、CI 定时评测、前端消费更细粒度 citation。当前已验证的一组核心回归为 `28 passed, 1 warning`。

当前主执行路径：

- 文档解析：`backend/app/services/document_parser.py`
- 文档入库与切块：`backend/app/services/rag_ingestion.py`
- 兼容层：`backend/app/services/rag.py`
- 上传入口：`backend/app/api/endpoints/documents.py`

## 已完成

### 1. 测试与运行基础打通

状态：已完成

已落地：

- 新增 `backend/pytest.ini`
- 新增 `backend/tests/conftest.py`
- 测试可直接导入 `app.*`
- 基础回归测试已可执行

备注：

- 当前 `pytest` 仍有 cache 目录 warning，但不影响功能验证。

### 2. 文档解析能力

状态：基础完成

已落地：

- 新增 `backend/app/services/document_parser.py`
- 支持 `txt`
- 支持基础 `docx`
- 支持基础文本型 `pdf`
- 不支持的文件类型会显式报错，不再直接进入 RAG

当前行为：

- 上传链路已改成“先解析，再上传，再入库”
- 非支持格式不会先落 MinIO 和数据库

限制：

- PDF 解析是最小实现，只覆盖简单文本型 PDF
- 扫描件、复杂排版、加密 PDF、图片型 PDF 尚未支持

### 3. 切块基础能力

状态：部分完成

已落地：

- 新增可测试的 `split_document_text()`
- 支持长文本按 `chunk_size/chunk_overlap` 切块
- 已覆盖“标题 + 空行 + 正文”的合并场景
- 已补 `test_chunking.py`、`test_chunking_rules.py`

限制：

- 当前切块还没有真正保存 `page_number`、`section_title`、`source_span`
- 仍属于规则型 chunking，不是最终生产版

### 4. Embedding provider 边界

状态：部分完成

已落地：

- 新增 `backend/app/services/embeddings.py`
- `rag_ingestion.py` 和 `chat.py` 已改为通过 provider 获取 embedding 能力
- 已支持 `mock` 和 `openai` 两种 provider
- provider 选择已改为运行时获取，不再在模块导入阶段固化
- 已新增 `scripts/validate_embeddings.py` 用于外部探测
- embedding 实现已切到 `openai` 原生客户端，避免 `langchain-openai` 的本地 tokenizer 依赖
- 已新增 `backend/.env.example`，提供“MiMo 聊天/重排 + OpenAI embeddings”的参考配置

限制：

- 默认 provider 仍是 mock
- Xiaomi MiMo 网关的真实外部探测已执行，当前 `embeddings` 路径返回 `404 Not Found`
- 现阶段结论是：MiMo 可用于聊天/重排，不可直接作为当前 embedding provider 使用

### 5. 文档入库失败兜底

状态：已完成

已落地：

- `Document` 增加 `failed_reason`
- 新增 Alembic 迁移：
  `backend/alembic/versions/5c8b4c7a9e21_add_failed_reason_to_documents.py`
- `process_document()` 成功时清空 `failed_reason`
- `process_document()` 失败时写入异常摘要并将状态置为 `failed`

### 6. RAG 入库实现解耦

状态：已完成

已落地：

- 新增 `backend/app/services/rag_ingestion.py` 作为干净的入库实现承载模块
- `backend/app/api/endpoints/documents.py` 已直接切到 `rag_ingestion.py`
- `backend/app/services/rag.py` 仅保留兼容层用途

## 部分完成

### 7. 兼容层清理

状态：已完成

已落地：

- 主执行路径已经不再依赖旧 `rag.py`
- `backend/app/services/rag.py` 已压缩为最小兼容层
- `backend/app/services/rag_ingestion.py` 已重写为干净 UTF-8 版本
- 旧测试和新测试都可通过

### 8. 基础测试矩阵

状态：部分完成

已落地：

- 文档解析测试
- 切块测试
- 入库成功/失败测试
- 上传接口测试
- embedding provider 基础测试
- 运行时 provider 选择测试
- query 预处理测试
- 对话上下文检索测试
- 结构化检索结果 / reranker hook 测试
- SSE/聊天链路测试
- 配额回退测试
- Storage 延迟初始化测试
- 离线评测指标测试

当前通过的回归覆盖范围：

- `tests/test_main.py`
- `tests/services/test_storage.py`
- `tests/services/test_rag.py`
- `tests/services/test_rag_ingestion.py`
- `tests/services/test_rag_failure_reason.py`
- `tests/services/test_chunking.py`
- `tests/services/test_chunking_rules.py`
- `tests/services/test_document_parser.py`
- `tests/services/test_embeddings.py`
- `tests/services/test_embedding_runtime_selection.py`
- `tests/services/test_query_rewrite.py`
- `tests/services/test_conversation_context.py`
- `tests/services/test_quota.py`
- `tests/services/test_chat_retrieval_preprocessing.py`
- `tests/services/test_chat_retrieval_reranking.py`
- `tests/services/test_statement_citations.py`
- `tests/services/test_structured_statement_extraction.py`
- `tests/services/test_rag_evaluation.py`
- `tests/services/test_rag_evaluation_extended.py`
- `tests/services/test_storage_lazy_init.py`
- `tests/api/test_documents.py`
- `tests/api/test_chat.py`

限制：

- 检索质量测试还没有
- 离线评测样本仍偏少

## 未开始

### 9. 去掉 mock LLM 输出

状态：部分完成

已落地：

- 新增 `backend/app/services/llm.py`
- `backend/app/api/endpoints/biz/chat.py` 已改为通过 `get_llm_provider()` 获取流式生成能力
- 已新增 `LLM_PROVIDER`、`CHAT_MODEL` 配置项
- 已支持 OpenAI 兼容网关 provider，可用于接入 Xiaomi MiMo
- 本地 `backend/.env` 已切到 Xiaomi MiMo 配置

未完成项：

- 还没有除 OpenAI 兼容外的其他真实模型 provider
- 还没有统一的 prompt / token 统计 / 错误映射层

### 10. 检索链路两阶段化

状态：部分完成

已落地：

- `backend/app/services/chat.py` 已新增 `RetrievedChunk`
- 检索结果已开始保留 `fused_score`、`final_score`、`sources`、rank 信息
- 已增加 `retrieve_ranked_chunks()`，旧 `retrieve_chunks()` 仍保持兼容
- 已接入 `backend/app/services/reranker.py` 作为 reranker provider 壳层
- 已支持 `RERANKER_PROVIDER=noop/simple` 配置切换
- 已支持 OpenAI 兼容 reranker provider，可复用 Xiaomi MiMo 网关
- 缓存已升级为结构化缓存，保留排序与分数信息
- reranker 失败时已明确降级回 fused ranking，而不是静默吞掉

未完成项：

- 真实 reranker 已可配置，但线上可用性仍受账户余额影响

### 11. Query Rewrite

状态：部分完成

已落地：

- 新增 `backend/app/services/query_rewrite.py`
- 新增 `backend/app/services/conversation_context.py`
- 已实现 `normalize_query()`、`rewrite_query()`、`prepare_retrieval_query()`
- `chat.py` 的 cache key、embedding query、关键词检索都已统一走 `retrieval_query`
- `biz/chat.py` 已开始结合最近会话消息构造 contextual retrieval query

未完成项：

- 目前仍是规则型预处理，不是多轮语义改写
- 当前只做最近消息拼接，不是完整的会话压缩
- 没有医疗术语别名扩展

### 12. Metadata Filter

状态：部分完成

已落地：

- `chat.py` 检索入口已支持 `document_ids`
- `chat.py` 检索入口已支持 `file_types`
- filter 条件已进入向量检索和关键词检索 SQL
- cache key 已纳入 filter 条件，避免不同过滤条件命中同一缓存
- `biz/chat.py` 已支持从请求体接收 `document_ids` / `file_types` 并透传到检索层

未完成项：

- 还没有面向业务层的 filter 构造器
- 还没有患者维度、时间范围、来源标签等更细粒度 filter

### 13. 结构化 Prompt

状态：部分完成

已落地：

- `build_rag_prompt()` 已改为结构化回答约束
- 已要求输出 `Conclusion / Evidence / Uncertainty`
- citation 已附带可展示的 `snippet`
- 已进一步要求 `Conclusion / Evidence` 句子显式带 `[Doc n]`

未完成项：

- 还没有按业务场景拆分 prompt 模板
- 还没有冲突证据优先级规则
- 还没有拒答质量评测

### 14. 可核查 Citation

状态：部分完成

已落地：

- citation 已包含 `doc_id`、`ref`、`page`、`snippet`
- citation 已包含 `chunk_id`
- citation 已包含 `chunk_index`
- citation 已包含 `source_span`
- 聊天链路已新增 `statement_citations`，可把回答中的 `[Doc n]` 映射回具体 citation
- `done` 事件已返回 `statement_citations`
- `statement_citations` 已兼容 `Doc 1`、`[Doc1]`、`[Doc 1]` 等格式
- 聊天链路已新增结构化抽取后处理，`statement_citations` 不再仅依赖模型内联 `Doc n`

未完成项：

- 前端还没消费更细粒度 citation

### 15. 多轮对话与 RAG 解耦

状态：部分完成

已落地：

- 已新增 `conversation_context.py`
- 聊天检索入口已开始区分 `raw_query` 和 `retrieval_query`
- 对短追问、代词型追问会结合最近 user message 扩展检索 query

未完成项：

- 还没有严格的历史压缩策略
- 还没有把 assistant 历史摘要化后再进入检索
- 还没有为多轮追问建立专项评测集

### 16. 观测指标

状态：部分完成

已落地：

- assistant message metadata 已新增 `observability`
- 当前已记录 `raw_query`、`retrieval_query`、`normalized_query`
- 当前已记录 `retrieved_chunk_count`、`citation_count`、`statement_count`
- 当前已记录 `llm_model`

未完成项：

- 还没有统一日志表或埋点导出
- 还没有记录首 token 延迟、总耗时、provider 降级原因
- 还没有接入可视化观测面板

### 17. 配额与缓存重构

状态：部分完成

已落地：

- 检索缓存已升级为结构化缓存，保留排序与分数
- Redis miss 时，聊天流式配额检查已支持回退数据库
- 聊天 metadata 已拆分 `input/output` token 统计

未完成项：

- 还没有检索缓存命中率指标
- 还没有更精确的 provider 级成本统计
- 还没有把回答缓存与检索缓存彻底分层

### 18. 外部依赖初始化去副作用

状态：部分完成

已落地：

- 测试环境已能通过 mock 隔离 MinIO
- `storage.py` 已改为 `get_storage_service()` 延迟初始化
- Redis 已改为 `get_redis_client()` 延迟初始化代理

未完成项：

- LLM / 真实 embedding provider 仍未统一做单例或生命周期管理

### 19. 离线评测闭环

状态：部分完成

已落地：

- 新增 `tests/fixtures/rag_cases.json`
- 新增 `app/services/rag_evaluation.py`
- 新增 `scripts/evaluate_rag.py`
- 当前已支持 `recall_at_k`、`answer_match_rate`、`citation_hit_rate`
- `citation_hit_rate` 已收紧为更保守的全匹配口径
- 当前已支持 `refusal_match_rate`、`avg_latency_ms`、`avg_total_tokens`

未完成项：

- 样本集仍是 demo 级，数量太少
- 还没有真实线上问答回放
- 还没有接入 CI 定时回归

## 当前优先级建议

### P0 已完成的部分

- 测试入口打通
- 文档解析基础能力
- 基础切块能力
- embedding provider 结构准备
- 入库失败兜底

### P0 仍需继续

- 接入真实可用的 embedding provider
- 统一 LLM / embedding provider 生命周期管理

### P1 建议下一步直接做

1. 接入真实 embedding provider
2. 扩充离线评测集并接入 CI
3. 增加业务级 filter 与多轮专项评测

## 当前验收状态

已满足：

1. 上传真实 `txt/docx/pdf` 样本后，系统可以完成基础解析与入库
2. 文档解析失败时不会继续上传和入库
3. 后台入库失败时会落 `failed` 状态并记录 `failed_reason`
4. RAG 入库主链路已有自动化测试保护
5. 检索链路已支持 query 预处理、上下文型 retrieval query、结构化结果和 reranker 接口壳层
6. 聊天链路已具备基础观测元数据、statement-citation 映射和 Redis miss 配额回退

尚未满足：

1. 同一问题 3 次检索结果稳定
2. 无证据时可靠拒答
3. prompt / retrieval / embedding 改动后的离线评测闭环覆盖真实样本


