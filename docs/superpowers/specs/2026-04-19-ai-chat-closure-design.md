# AI 问答模块闭环修复 — 设计规格书

> **文档版本**: 1.0
> **日期**: 2026-04-19
> **状态**: 已审批
> **关联分析**: 基于 AI 问答模块全链路分析报告中识别的 10 个未闭环问题

---

## 1. 目标

将 AI 问答模块从"可运行的原型"升级为"生产可用的闭环系统"，解决以下核心问题：

1. 会话数据存内存 Map，重启丢失
2. 多租户/组织隔离完全缺失
3. 知识库/文档删除不清理 Milvus 向量和 MinIO 文件
4. RAG 引用元数据未透传到前端
5. SSE 事件过滤过度（工具调用状态丢弃）
6. 文档解析仅支持纯文本 UTF-8
7. Milvus 表达式注入风险
8. LangGraph 同步调用阻塞事件循环
9. 会话历史无限增长无截断
10. 系统提示词过于简陋

## 2. 架构概览

### 2.1 变更前后对比

**变更前**：
```
Gateway :8001 ──TCP──▶ patient-service :8021 (含 knowledge 模块)
         │
         ├──HTTP──▶ Agent :8000
         │
         └─ 内存 Map 存会话
```

**变更后**：
```
Gateway :8001 ──TCP──▶ patient-service :8021 (纯患者域)
         │
         ├──TCP──▶ ai-service :8031 (知识库 + 会话 + 消息)
         │
         └──HTTP──▶ Agent :8000 (+删除API +格式支持 +引用Artifact)
```

### 2.2 核心设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 会话归属 | 新建 `ai-service` 微服务 | 知识库 + 会话 = "AI 问答"限界上下文，与患者域无关联 |
| 多租户校验层级 | Gateway 层校验 + Milvus 防御过滤 | Agent 保持纯 AI 引擎定位，不承担业务鉴权 |
| 向量清理 | Agent 暴露删除 API | Milvus 读写由 Agent 统一管理（单一职责） |
| 上下文管理 | `langchain_core.messages.trim_messages()` | LangChain 原生 API，项目已有 tiktoken 依赖 |
| 引用传递 | `@tool(response_format="content_and_artifact")` | LangChain 原生 Artifact 机制，元数据与内容分离 |
| 文档格式 | PDF + DOCX + TXT + Markdown | 覆盖慢病管理场景常见素材格式 |

---

## 3. 数据库 Schema

新增两张表到 `database/init.sql`：

```sql
-- -----------------------------------------------------------
-- conversations - 会话表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id               BIGINT       PRIMARY KEY,
    tenant_id        BIGINT       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id           BIGINT       NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id          BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kb_id            BIGINT       REFERENCES knowledge_bases(id) ON DELETE SET NULL,
    title            VARCHAR(100) NOT NULL DEFAULT '新对话',
    message_count    INTEGER      NOT NULL DEFAULT 0,
    total_tokens     INTEGER      NOT NULL DEFAULT 0,
    last_message_at  TIMESTAMP    NOT NULL DEFAULT now(),
    created_at       TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at       TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_conversations_user
    ON conversations (tenant_id, user_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_org
    ON conversations (tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_conversations_kb
    ON conversations (kb_id) WHERE kb_id IS NOT NULL;

-- -----------------------------------------------------------
-- chat_messages - 聊天消息表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id              BIGINT      PRIMARY KEY,
    conversation_id BIGINT      NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT        NOT NULL,
    citations       JSONB,
    metadata        JSONB,
    token_count     INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMP   NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conv
    ON chat_messages (conversation_id, created_at);
```

### Schema 设计原则

- **复数表名**：与 `tenants`, `users`, `organizations` 等保持一致
- **雪花 ID**：`BIGINT PRIMARY KEY`，应用层 `nextId()` 生成
- **软删除**：`deleted_at TIMESTAMP`，与全库一致
- **时间戳类型**：`TIMESTAMP NOT NULL DEFAULT now()`，与全库一致
- **FK 策略**：`kb_id` 使用 `ON DELETE SET NULL`（知识库删除不影响会话）
- **统计字段**：`message_count` / `total_tokens` / `last_message_at` 避免聚合查询

---

## 4. ai-service 微服务

### 4.1 目录结构

```
backend-nestjs/apps/ai/
├── src/
│   ├── main.ts                          # TCP 启动 :8031
│   ├── app.module.ts                    # 根模块
│   ├── knowledge/                       # 从 patient-service 平移
│   │   ├── entities/
│   │   │   ├── knowledge-base.entity.ts
│   │   │   └── document.entity.ts
│   │   ├── knowledge.controller.ts
│   │   ├── knowledge.module.ts
│   │   └── knowledge.service.ts
│   └── conversation/                    # 新增
│       ├── entities/
│       │   ├── conversation.entity.ts
│       │   └── chat-message.entity.ts
│       ├── conversation.controller.ts
│       ├── conversation.module.ts
│       └── conversation.service.ts
├── nest-cli.json
├── package.json
└── tsconfig.json
```

### 4.2 TCP 命令常量

新增到 `libs/shared/src/constants.ts`：

```typescript
export const AI_SERVICE = 'AI_SERVICE';
export const AI_TCP_PORT = 8031;

export const CONVERSATION_FIND_ALL   = 'conv_find_all';
export const CONVERSATION_FIND_ONE   = 'conv_find_one';
export const CONVERSATION_CREATE     = 'conv_create';
export const CONVERSATION_DELETE     = 'conv_delete';
export const MESSAGE_CREATE          = 'msg_create';
export const KB_VERIFY_OWNERSHIP     = 'kb_verify_ownership';
```

### 4.3 ConversationService 方法

| 方法 | 职责 |
|------|------|
| `findAll(tenantId, userId)` | 查询用户会话列表，按 `last_message_at DESC` 排序 |
| `findOne(id, tenantId, userId)` | 获取单个会话 + 关联消息 |
| `create(tenantId, orgId, userId, kbId, title)` | 创建会话（雪花 ID） |
| `delete(id, tenantId, userId)` | 软删除会话 |
| `createMessage(conversationId, role, content, citations?, metadata?, tokenCount?)` | 创建消息 + 事务更新会话统计 |
| `verifyKbOwnership(kbId, tenantId)` | 校验知识库是否属于该租户 |

### 4.4 从 patient-service 迁出

- **平移文件**：`patient/src/knowledge/` 整个目录迁到 `ai/src/knowledge/`
- **删除来源**：patient-service 的 `app.module.ts` 移除 `KnowledgeModule` import
- **Gateway 路由更新**：`KnowledgeBaseProxyController` 和 `KnowledgeDocumentProxyController` 的 `@Inject(PATIENT_SERVICE)` 改为 `@Inject(AI_SERVICE)`

---

## 5. Gateway 变更

### 5.1 新增 ai-service 客户端

`app.module.ts` 的 `ClientsModule.register` 新增：

```typescript
{
  name: AI_SERVICE,
  transport: Transport.TCP,
  options: { host: process.env.AI_HOST || 'localhost', port: Number(process.env.AI_TCP_PORT) || AI_TCP_PORT },
},
```

### 5.2 AgentProxyService 重构

**核心变更：删除 `private conversations = new Map<string, ChatConversation>()`**

所有会话操作改为 TCP 调用 ai-service：

| 方法 | 变更 |
|------|------|
| `getConversations` | TCP `CONVERSATION_FIND_ALL` |
| `getConversation` | TCP `CONVERSATION_FIND_ONE` |
| `deleteConversation` | TCP `CONVERSATION_DELETE` |
| `createConversation` | 删除，由 `streamChat` 内部调用 |

### 5.3 streamChat 重构流程

```
1. 收到 POST /api/v1/chat { kb_id, query, conversation_id? }
2. TCP → ai-service: KB_VERIFY_OWNERSHIP(kb_id, tenantId) → 失败返回 403
3. 若无 conversation_id:
   TCP → ai-service: CONVERSATION_CREATE → 获得 convId
4. TCP → ai-service: MESSAGE_CREATE(convId, 'user', query)
5. TCP → ai-service: CONVERSATION_FIND_ONE(convId) → 获取历史消息
6. HTTP → Agent: POST /internal/chat { query, history, metadata: { kb_id } }
7. 流式转发（含新事件类型，见 5.4）
8. 流结束: TCP → ai-service: MESSAGE_CREATE(convId, 'assistant', content, citations, metadata, tokenCount)
9. SSE → 前端: { done: true }
```

### 5.4 SSE 事件透传

| Agent 事件 | Gateway 转发 | 用途 |
|-----------|-------------|------|
| `message` | `{ text: "..." }` | 文本流 |
| `tool_start` | `{ tool_start: { name, input } }` | 前端显示"正在检索…" |
| `tool_end` | `{ tool_end: { name }, citations: [...] }` | 引用数据 + 检索完成态 |
| `error` | `{ error: "..." }` | 错误提示 |

Gateway 从 `tool_end` 事件的 `artifact` 字段提取结构化引用数据。

### 5.5 知识库删除联动

文档删除流程：
```
1. TCP → ai-service: 获取文档详情（kb_id, minio_url）
2. HTTP → Agent: DELETE /internal/knowledge/vectors?kb_id=xxx&filename=yyy
3. MinIO: 删除原始文件
4. TCP → ai-service: DOCUMENT_DELETE
```

知识库删除流程：
```
1. HTTP → Agent: DELETE /internal/knowledge/vectors?kb_id=xxx  (全量清理)
2. MinIO: 批量删除该 KB 下文件
3. TCP → ai-service: KNOWLEDGE_BASE_DELETE  (CASCADE 自动删文档记录)
```

---

## 6. Agent (Python) 变更

### 6.1 新增向量删除端点

`app/routers/internal.py` 新增：

| 接口 | 用途 |
|------|------|
| `DELETE /internal/knowledge/vectors?kb_id=xxx&filename=yyy` | 删除特定文档向量 |
| `DELETE /internal/knowledge/vectors?kb_id=xxx` | 删除整个知识库向量 |

### 6.2 多格式文档解析

`app/agent/ingestion.py` 增加格式分流：

| 后缀 | 解析方式 | 新增依赖 |
|------|---------|---------|
| `.txt` | UTF-8 decode | 无 |
| `.md` | UTF-8 decode + 结构保留 | 无 |
| `.pdf` | `PyPDFLoader` | `langchain-community`, `pypdf` |
| `.docx` | `Docx2txtLoader` | `langchain-community`, `docx2txt` |

### 6.3 RAG 引用 Artifact 机制

使用 LangChain 原生 `content_and_artifact` 模式：

```python
@tool(response_format="content_and_artifact")
def rag_search_handler(query: str, config: RunnableConfig) -> tuple[str, list[dict]]:
    # 检索逻辑...
    context = "\n\n".join([f"[Doc {i+1}] {doc.page_content}" for i, doc in enumerate(docs)])
    citations = [
        {"ref": f"Doc {i+1}", "source": doc.metadata.get("filename"),
         "snippet": doc.page_content[:200], "page": doc.metadata.get("page")}
        for i, doc in enumerate(docs)
    ]
    return context, citations  # (LLM 内容, 前端元数据)
```

- `.content` = 文本上下文（LLM 使用）
- `.artifact` = 结构化引用（不进 LLM 上下文，纯元数据透传）

### 6.4 上下文窗口管理

`graph.py` 的 `assistant_node` 使用 `trim_messages()`：

```python
from langchain_core.messages import trim_messages

messages = trim_messages(
    messages,
    max_tokens=4000,
    token_counter=llm,
    strategy="last",
    start_on="human",
    include_system=True,
)
```

### 6.5 异步修复

`assistant_node` 改为 `async def`，`llm.invoke()` → `await llm.ainvoke()`。

### 6.6 Milvus 表达式安全

```python
import re
if not re.match(r'^[\w-]+$', kb_id):
    return "知识库 ID 格式无效"
search_kwargs = {"expr": f'kb_id == "{kb_id}"'}
```

### 6.7 系统提示词增强

```python
SYSTEM_PROMPT = """你是慢病管理平台的 AI 健康顾问。

## 角色定位
- 基于知识库中的专业医疗文献为用户提供循证健康建议
- 回答必须使用中文

## 工具使用规范
- 当用户提出与疾病管理、药物、检查指标相关的问题时，必须先调用 rag_search_handler 检索知识库
- 当问题是日常寒暄或与医疗无关时，直接回答即可

## 回答格式
- 引用知识库内容时使用 [Doc N] 标记
- 涉及医疗建议时，始终提醒用户"具体方案请咨询主治医师"
- 使用 Markdown 格式提升可读性
"""
```

---

## 7. 前端适配

### 7.1 SSE 新事件处理

`pages/chat/index.tsx` 的 `handleSend` 新增事件处理：

| payload 字段 | 处理 |
|-------------|------|
| `citations` | 更新 `currentCitations`（现有逻辑已支持） |
| `tool_start` | 设置 `searching = true` |
| `tool_end` | 设置 `searching = false` |
| `error` | 调用 `appMsg.error()` |
| `done` | 替代原来的 `tokens`，刷新会话列表 |

### 7.2 检索状态提示

新增 `searching` 状态，在 assistant 消息气泡内显示：

```tsx
{searching && <Tag color="processing" icon={<LoadingOutlined />}>正在检索知识库…</Tag>}
```

### 7.3 Citation 类型统一

```typescript
interface Citation {
  ref: string;        // "Doc 1"
  source: string;     // 文件名
  snippet: string;    // 内容摘要
  page?: number;      // PDF 页码
}
```

---

## 8. 新增依赖清单

### Agent (pyproject.toml)
```
langchain-community    # PyPDFLoader, Docx2txtLoader
pypdf                  # PDF 解析
docx2txt               # DOCX 解析
```

### backend-nestjs
无新增外部依赖。ai-service 复用现有 Monorepo 依赖。

### 前端
无新增依赖。

---

## 9. 端口分配（更新后）

| 服务 | 协议 | 端口 | 说明 |
|------|------|------|------|
| Gateway | HTTP | 8001 | 统一 API 入口 |
| Auth Service | TCP | 8011 | 用户/组织/RBAC |
| Patient Service | TCP | 8021 | 患者/健康指标（不再含知识库） |
| **AI Service** | **TCP** | **8031** | **知识库 + 会话 + 消息（新增）** |
| Agent | HTTP | 8000 | AI 流式接口 |
