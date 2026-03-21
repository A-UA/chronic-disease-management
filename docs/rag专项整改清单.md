# RAG 专项整改清单

## 目标

把当前 demo 级 RAG，整改为“可入库、可检索、可回答、可引用、可评测、可运维”的最小可用生产版本。

## 现状判断

当前链路已经有上传、切块、检索、流式输出的外壳，但核心仍是 mock，且入库质量、检索质量、引用可信度、测试闭环都不足。

## 范围

重点覆盖以下模块：

- `backend/app/api/endpoints/documents.py`
- `backend/app/services/rag.py`
- `backend/app/services/chat.py`
- `backend/app/api/endpoints/biz/chat.py`
- `backend/app/services/quota.py`
- `backend/app/services/storage.py`
- `backend/tests/...`

---

## 第一阶段：先把主链路做实

### 1. 文档解析能力补齐

- 问题：上传后只做 `utf-8` 解码，PDF、Word、扫描件基本不可用。
- 改造：
- 新增文档解析层，区分 `txt/pdf/docx`。
- 保存抽取后的纯文本、页码、段落元数据。
- 失败文档记录 `failed_reason`，而不是统一塞占位文本。
- 涉及文件：
- 修改 `backend/app/api/endpoints/documents.py`
- 修改 `backend/app/services/rag.py`
- 建议新增 `backend/app/services/document_parser.py`
- 验收：
- PDF、DOCX、TXT 至少各 1 个样例可成功抽取。
- 非文本文件不会被当成有效知识入库。

### 2. 切块策略重做

- 问题：`backend/app/services/rag.py` 中中文分隔符乱码，当前 chunking 不可信。
- 改造：
- 统一 UTF-8 编码。
- 按“标题/段落/页码”切块，而不是单纯字符切块。
- 为 chunk 保存 `page_number`、`section_title`、`chunk_index`、`source_span`。
- 医疗文本增加规则：主诉、现病史、既往史、检查、诊断、建议等优先保留边界。
- 涉及文件：
- 修改 `backend/app/services/rag.py`
- 建议新增 `backend/tests/services/test_chunking.py`
- 验收：
- 同一段医学语义不被无意义截断。
- 中文标题和章节边界可稳定识别。

### 3. 去掉 mock embedding

- 问题：`backend/app/services/rag.py` 和 `backend/app/services/chat.py` 的向量是固定值，语义检索无效。
- 改造：
- 抽象 embedding provider。
- 支持 `mock` 和 `real` 两套实现，环境变量切换。
- 入库和查询统一走同一个 embedding 接口。
- 涉及文件：
- 修改 `backend/app/services/rag.py`
- 修改 `backend/app/services/chat.py`
- 建议新增 `backend/app/services/embeddings.py`
- 验收：
- 不同 query 生成不同向量。
- 检索结果不再随便命中。

### 4. 去掉 mock LLM 输出

- 问题：`backend/app/api/endpoints/biz/chat.py` 仍是伪流式响应。
- 改造：
- 抽象 chat model provider。
- 支持真实流式生成。
- 保留 mock 仅用于测试环境。
- 涉及文件：
- 修改 `backend/app/api/endpoints/biz/chat.py`
- 建议新增 `backend/app/services/llm.py`
- 验收：
- SSE 输出来自真实模型。
- 模型异常可中断并返回结构化错误。

## 第二阶段：把检索质量拉起来

### 5. 检索链路拆成两阶段

- 问题：`backend/app/services/chat.py` 只有粗糙 hybrid search + RRF，没有精排。
- 改造：
- 第一阶段：向量召回 + 关键词召回。
- 第二阶段：reranker 精排。
- 为每个候选 chunk 输出 `recall_score`、`rerank_score`。
- 涉及文件：
- 修改 `backend/app/services/chat.py`
- 建议新增 `backend/app/services/retriever.py`
- 建议新增 `backend/app/services/reranker.py`
- 验收：
- top-k 结果更稳定。
- 同义表达、口语表达的命中率明显提升。

### 6. 增加 query rewrite

- 问题：医疗问答常见口语、别名、缩写，直接拿原问题检索效果有限。
- 改造：
- 在检索前做问题标准化与改写。
- 输出原 query、rewrite query、检索 query，方便排查。
- 对短问题、追问、上下文依赖问题做补全。
- 涉及文件：
- 修改 `backend/app/api/endpoints/biz/chat.py`
- 建议新增 `backend/app/services/query_rewrite.py`
- 验收：
- “这个药能继续吃吗”“血糖高怎么办”这类问法召回更稳定。
- 多轮追问不再大量跑偏。

### 7. 加 metadata filter

- 问题：目前只按 `org_id/kb_id` 过滤，粒度不够。
- 改造：
- 支持按文档类型、上传时间、患者维度、来源标签过滤。
- 检索接口保留 filter 扩展位。
- 涉及文件：
- 修改 `backend/app/services/chat.py`
- 对应模型字段如果缺失，再补 DB schema。
- 验收：
- 可以限制只在指定知识域里回答。
- 降低跨文档误召回。

## 第三阶段：把回答质量和引用可信度做起来

### 8. Prompt 结构化

- 问题：`backend/app/services/chat.py` 的 prompt 太弱，容易幻觉。
- 改造：
- 强制输出固定结构：结论、依据、风险提示、无法判断时的拒答。
- 明确要求“只依据提供证据回答”。
- 对冲突证据要求说明差异。
- 涉及文件：
- 修改 `backend/app/services/chat.py`
- 建议新增 `backend/app/services/prompts.py`
- 验收：
- 无证据时明确拒答。
- 有证据时回答更稳定，格式一致。

### 9. 引用从装饰改成可核查

- 问题：当前 citation 只是 `Doc 1/2/...`，可信度不够。
- 改造：
- 每条回答绑定具体 chunk 引用。
- 引用里返回文档名、页码、片段摘要、chunk_id。
- 后续可扩展到句子级引用。
- 涉及文件：
- 修改 `backend/app/services/chat.py`
- 修改 `backend/app/api/endpoints/biz/chat.py`
- 验收：
- 前端可直接展示“引用来源”。
- 开发调试时能快速定位错误召回。

### 10. 多轮对话与 RAG 解耦

- 问题：当前更像“每轮单独问答 + 简单存消息”，历史上下文没有真正参与检索。
- 改造：
- 会话层负责整理历史。
- 检索层只接收经过压缩或改写后的检索 query。
- 生成层再使用必要历史上下文。
- 涉及文件：
- 修改 `backend/app/api/endpoints/biz/chat.py`
- 建议新增 `backend/app/services/conversation_context.py`
- 验收：
- 用户追问时检索更准。
- 不会把整段历史无脑拼进 prompt。

## 第四阶段：把系统做成可运营、可排障

### 11. 建立观测指标

- 问题：当前出了错只能看代码，几乎没可观测性。
- 改造：
- 记录每次问答的 query、rewrite、召回 chunk、模型耗时、token、拒答原因。
- 为文档入库记录 parse、chunk、embed 各阶段耗时。
- 涉及文件：
- 修改 `backend/app/api/endpoints/biz/chat.py`
- 修改 `backend/app/services/rag.py`
- 可复用 `UsageLog` 或新增专门日志表。
- 验收：
- 能回答“为什么这次答错了”“为什么这次没命中”。

### 12. 配额与缓存策略重构

- 问题：`backend/app/services/quota.py` 中 Redis miss 直接放行，token 还是粗估。
- 改造：
- 输入 token、输出 token 分开计量。
- 缓存命中只做加速，不作为唯一可信源。
- 检索缓存与回答缓存分离。
- 涉及文件：
- 修改 `backend/app/services/quota.py`
- 修改 `backend/app/api/endpoints/biz/chat.py`
- 修改 `backend/app/services/chat.py`
- 验收：
- 高并发下配额控制稳定。
- 缓存异常不会导致逻辑失真。

### 13. 依赖初始化去副作用

- 问题：`backend/app/services/storage.py` 导入即初始化外部依赖，测试与启动都脆弱。
- 改造：
- MinIO、Redis、LLM、Embedding 延迟初始化。
- 为测试注入 fake 或 mock provider。
- 涉及文件：
- 修改 `backend/app/services/storage.py`
- 修改相关 service 初始化方式。
- 验收：
- 单元测试不依赖真实 MinIO、Redis、LLM。
- 应用导入不会因外部服务未启动直接失败。

## 第五阶段：建立评测闭环

### 14. 补齐最小 RAG 测试矩阵

- 当前短板：测试链路未打通，RAG 核心没有有效回归保护。
- 改造：
- 单元测试：chunking、prompt、citation、quota。
- 集成测试：上传文档 -> 入库 -> 检索 -> SSE 输出。
- 回归测试：固定 20 到 50 条问答样本，比较命中与回答质量。
- 建议新增：
- `backend/tests/services/test_chunking.py`
- `backend/tests/services/test_retriever.py`
- `backend/tests/services/test_prompts.py`
- `backend/tests/api/test_rag_chat.py`
- `backend/tests/fixtures/rag_cases.json`
- 验收：
- 每次改 RAG 都能知道是否退化。
- 不再依赖人工“感觉变好了”。

### 15. 建立离线评测指标

- 建议最少跟踪：
- 检索命中率 Recall@k
- 引用正确率
- 拒答正确率
- 回答一致性
- 延迟和 token 成本
- 验收：
- 优化可以量化，不靠主观印象。

## 建议排期

### P0，本周必须做

- 文档解析
- 切块修复
- 去掉 mock embedding
- 去掉 mock LLM
- 打通基础测试

### P1，下周做

- query rewrite
- reranker
- 结构化 prompt
- 可核查 citation

### P2，随后做

- 多轮上下文优化
- 观测日志
- 配额精算
- 离线评测集

## 最关键的验收标准

1. 上传一份真实中文医疗文档后，系统能正确抽取文本并完成入库。
2. 同一个问题在 3 次测试中检索结果基本稳定。
3. 回答必须附带可核查引用。
4. 无证据时系统明确拒答，而不是编造。
5. 修改 prompt、chunking、embedding 后，有回归测试和离线评测支撑。
