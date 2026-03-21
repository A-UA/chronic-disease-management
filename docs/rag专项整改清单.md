# RAG 专项整改清单

更新时间：2026-03-22

## 当前结论

RAG 基础入库链路已经从 demo 外壳推进到“可解析、可切块、可入库、可失败兜底、可测试”的阶段，但检索质量、生成质量、引用可信度和评测闭环仍未开始建设。

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

- `backend/app/services/rag_ingestion.py` 中的中文标题常量仍存在编码污染
- 当前切块还没有真正保存 `page_number`、`section_title`、`source_span`
- 仍属于规则型 chunking，不是最终生产版

### 4. Embedding provider 边界

状态：结构完成，能力未完成

已落地：

- 新增 `backend/app/services/embeddings.py`
- `rag_ingestion.py` 和 `chat.py` 已改为通过 provider 获取 embedding 能力
- 默认 provider 仍是 mock

限制：

- 真实 embedding 模型还没接入
- 目前只是把“替换真实模型”的结构准备好了

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

状态：部分完成

已落地：

- 主执行路径已经不再依赖旧 `rag.py`
- 旧测试和新测试都可通过

遗留问题：

- `backend/app/services/rag.py` 已被压缩为兼容层，但工作区里该文件仍显示为已修改状态
- `backend/app/services/rag_ingestion.py` 内中文常量仍有编码问题，需要继续清理

### 8. 基础测试矩阵

状态：部分完成

已落地：

- 文档解析测试
- 切块测试
- 入库成功/失败测试
- 上传接口测试
- embedding provider 基础测试

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
- `tests/api/test_documents.py`

限制：

- 检索质量测试还没有
- prompt 回归测试还没有
- SSE/聊天链路测试还没有
- 离线评测集还没有

## 未开始

### 9. 去掉 mock LLM 输出

状态：未开始

未完成项：

- `backend/app/api/endpoints/biz/chat.py` 仍是 mock 流式输出
- 真实模型 provider 尚未接入

### 10. 检索链路两阶段化

状态：未开始

未完成项：

- 向量召回 + 关键词召回 + reranker 的两阶段检索还没实现
- `backend/app/services/chat.py` 仍是粗粒度 hybrid search + RRF

### 11. Query Rewrite

状态：未开始

### 12. Metadata Filter

状态：未开始

### 13. 结构化 Prompt

状态：未开始

### 14. 可核查 Citation

状态：未开始

### 15. 多轮对话与 RAG 解耦

状态：未开始

### 16. 观测指标

状态：未开始

### 17. 配额与缓存重构

状态：未开始

### 18. 外部依赖初始化去副作用

状态：部分完成

已落地：

- 测试环境已能通过 mock 隔离 MinIO

未完成项：

- `storage.py` 仍是导入即初始化
- Redis / LLM / 真实 embedding 仍未统一做延迟初始化

### 19. 离线评测闭环

状态：未开始

未完成项：

- `rag_cases.json` 不存在
- Recall@k、拒答率、引用正确率、回答一致性等指标还未建立

## 当前优先级建议

### P0 已完成的部分

- 测试入口打通
- 文档解析基础能力
- 基础切块能力
- embedding provider 结构准备
- 入库失败兜底

### P0 仍需继续

- 清理 `rag_ingestion.py` 的中文编码问题
- 接入真实 embedding provider
- 让 `storage.py`、后续 LLM/Redis 初始化更可控

### P1 建议下一步直接做

1. 接入真实 embedding provider
2. 清理 `rag_ingestion.py` 的中文标题规则和编码
3. 开始改造 `chat.py` 检索链路

## 当前验收状态

已满足：

1. 上传真实 `txt/docx/pdf` 样本后，系统可以完成基础解析与入库
2. 文档解析失败时不会继续上传和入库
3. 后台入库失败时会落 `failed` 状态并记录 `failed_reason`
4. RAG 入库主链路已有自动化测试保护

尚未满足：

1. 同一问题 3 次检索结果稳定
2. 回答附带可核查引用
3. 无证据时可靠拒答
4. prompt / retrieval / embedding 改动后的离线评测闭环
