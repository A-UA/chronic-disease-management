# Agent Middleware - 知识库内部解析上传路由 (Knowledge Parsing Endpoint) 设计规范

## 背景 (Context)
随着整个多端系统的重构完成，原有基于 Python 单体应用中的文件解析录入模块已被剥离遗失。为了在现有全新的 RAG（检索增强生成）流程中闭环其对应的文件维护链路，决定在 Python `agent` 微服务中设立一个轻量无状态的、只执行逻辑计算的内部文件解析管道。

## 系统架构与职责 (Architecture)
采用 **纯净解耦模式 (Decoupled Mode)**:
1. **Java/NestJS 业务主服务:** 保有原有关于 RAG 的 PostgreSQL（元数据）状态持久权。包含租户控制、`Documents` 列状态、存储凭证管理。所有来自客户端页面的新文档将由以上两套主服务其中之一进行中转代理。
2. **Python Agent 并发中间层:** 提供 `POST /internal/knowledge/parse` 接口。专注于在内存中洗练、切片文本并且在无状态情景下只负责把转换好的高维向量片段塞入 Milvus。

## 详细设计 (Detailed Design)

### 1. 内部路由 (Internal API Definition)
**Endpoint**: `POST /internal/knowledge/parse`

**Request:** 
- `Content-Type: multipart/form-data`
- Body 参数:
  - `file`: 传入的具体文件格式缓冲二进制流 (File)
  - `kb_id`: 以字符串形式穿透进入的租户属下确切的知识库 ID。

**Response:** 
- JSON 对象:
  ```json
  {
      "status": "success",
      "filename": "demo.txt",
      "chunk_count": 42
  }
  ```

### 2. 文本解析处理流 (LangChain ETL Pipeline)
1. **环境准备:** 添加必要依赖至 `pyproject.toml`。如 FastAPI 需要 `python-multipart` 来读取上传流。
2. **清洗分离加载 (Document Loaders):**
   * 取决于 `file.filename` 的扩展后缀判定内容装载器。
   * 第一阶段首先重点保障 `.txt`, `.md` 常规文本的可靠切片加载直接支持。
3. **字符切片 (Text Splitter):**
   * 使用带有良好断句能力的 `RecursiveCharacterTextSplitter`。
   * **分片尺寸 (Chunk Size):** ~1000 Tokens/字符
   * **连贯性交叠 (Chunk Overlap):** ~150 Tokens/字符，确保跨段落关联文不会被腰斩。
4. **生成与固态化 (Embeddings into Milvus):**
   * 直接重用 `agent.tools.rag_tool` 当前采用的自定义远端大模型配置（针对 `DashScope` 或 `OpenAI` 兼容代理）。
   * 对所有的 Document `metadata` 强行覆盖附加 `kb_id: {传入值}` 绑定标签。
   * 调用 `Milvus.add_documents()` 追加至指定的 Collection 中 `cdm_kb`。

### 3. 数据流示例 (Data Flow Matrix)
1. **用户**上传文档通过 Web 前端至 **网关服务**。
2. **网关服务**创建一条 `status = 'pending'` 记录写入自身管理的 PG DB，并通过内网下发原文件（或存储直链）及该 `kb_id` 给 **Agent微服务**。
3. **Agent 微服务**的 `/parse` 阻塞接管并执行上文中的 AI 计算。
4. **Agent 微服务**计算落库并向内网响应 `{ chunk_count: N }`。
5. **网关服务**拦截内网响应，把 PG 数据库中此表的状态更新为 `completed`、记录下具体的 `chunk_count` 返回前端即可闭环。

## 局限与优化项 (Limitations & Expansion)
- **同步压力与时序问题：** 由于目前使用的是标准的 FastAPI HTTP 同步模型响应机制，几十兆乃至更大数据集解析会有接口超时挂起的弊端。初期以 10M 以下单文件快速响应做主打，应对较大型语料包可以考虑将来引入 Celery 或让 Java Gateway 层采用轮询检查回调模式拓展。
