# 多租户 AI SaaS 架构设计文档

## 1. 系统架构概览

- **核心数据库**：PostgreSQL，用于存储所有关系型数据。
- **向量检索引擎**：pgvector 插件（部署在同一 PostgreSQL 实例中），实现向量数据的统一存储与管理，降低运维复杂度。
- **对象存储**：MinIO，用于存储用户上传的原始文件（如 PDF、Word），提供 S3 兼容的存储方案。
- **隔离级别**：逻辑隔离（Logical Isolation / Row-level）。所有核心表统一增加 `org_id` 字段。建议开启 PostgreSQL 的 RLS (Row-Level Security) 防止越权访问。
- **用户模型**：多对多模式。一个用户可以加入多个组织（Organization），并在组织间切换。

## 2. 核心数据流

1.  **知识上传**：用户创建知识库 -> 上传文件 -> 保存到 MinIO 获 URL -> 在 PostgreSQL 生成 `documents` 记录并关联 `kb_id` -> 后台解析文档进行分块（Chunking）-> 调用大模型生成 Embedding -> 存入带有 `kb_id` 和 `org_id` 的 `chunks` 表中。
2.  **问答检索 (RAG & Streaming)**：
    *   **历史组装**：从 `messages` 提取当前对话历史上下文。
    *   **意图识别与改写 (可选)**：结合历史记录，将用户当前提问改写为独立的搜索词。
    *   **向量检索**：对改写后的查询词进行 Embedding，在 `chunks` 表中过滤 `kb_id` 获取 Top K 的文本块。
    *   **Prompt 拼装**：将检索到的文本块与用户问题组合为最终 Prompt。
    *   **流式响应 (SSE)**：调用 LLM，通过 Server-Sent Events (SSE) 先推送参考文档列表 (meta)，然后逐字推送生成的文本 (chunk)，最后推送统计信息 (done)。
    *   **数据持久化**：将用户提问和完整回答（包含来源引用 `citations` 和 `tokens` 消耗）存入 `messages`，用量存入 `usage_logs`。

## 3. 数据模型设计 (Database Schema)

满足多租户 B2B 场景及多知识库管理的实体关系设计如下：

```sql
-- 1. 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 组织表 (租户)
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan_type VARCHAR(50) DEFAULT 'free', -- 订阅计划
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 组织与用户关联表 (实现多对多)
CREATE TABLE organization_users (
    org_id UUID REFERENCES organizations(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(50) DEFAULT 'member', -- owner, admin, member, viewer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (org_id, user_id)
);

-- 4. 知识库表 (Knowledge Bases)
CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    created_by UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_kb_org_id ON knowledge_bases(org_id);

-- 5. 文档表
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    kb_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) NOT NULL, -- 冗余隔离边界
    uploader_id UUID REFERENCES users(id),
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50), -- pdf, docx, txt
    file_size INT,
    minio_url VARCHAR(1024) NOT NULL,
    status VARCHAR(50) DEFAULT 'processing', -- pending, processing, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_documents_kb_id ON documents(kb_id);

-- 6. 文档切块表 (包含向量数据)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    kb_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) NOT NULL, -- 用于 RLS 和底层隔离
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INT,
    chunk_index INT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 针对当前知识库的向量检索索引 (过滤 kb_id 极大提升 RAG 精准度)
CREATE INDEX idx_chunks_kb_id ON chunks(kb_id);
-- (可选) HNSW 向量索引加速检索
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);

-- 7. 对话会话表
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    kb_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    user_id UUID REFERENCES users(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 聊天消息表 (支持引用来源与流式结果持久化)
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    metadata JSONB, -- 存储来源引用(citations)和 Token 消耗信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. 用量日志表 (计费与审计核心)
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    user_id UUID REFERENCES users(id), -- 如果是 API Key 调用，此字段可为 NULL
    api_key_id UUID, -- 关联的 API Key (外部调用时)
    
    -- 计费核心字段
    model VARCHAR(100) NOT NULL,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT GENERATED ALWAYS AS (prompt_tokens + completion_tokens) STORED,
    cost DECIMAL(10, 6) DEFAULT 0.0,
    
    action_type VARCHAR(50),
    resource_id UUID,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 针对账单查询和配额检查的索引
CREATE INDEX idx_usage_logs_billing ON usage_logs(org_id, created_at);

-- 10. API 密钥表 (支持外部调用)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    
    -- 安全存储: 原始 sk_... 仅展示一次
    key_prefix VARCHAR(20) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    
    -- 限制与配额
    qps_limit INT DEFAULT 10,
    token_quota BIGINT, -- 可选：单个 Key 的独立额度
    token_used BIGINT DEFAULT 0,
    
    status VARCHAR(50) DEFAULT 'active', -- active, revoked
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 4. 安全性与隔离策略

建议在数据库层面应用 Row-Level Security (RLS) 策略，以物理级别加强逻辑隔离。

```sql
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
CREATE POLICY chunks_isolation_policy ON chunks
    USING (org_id = current_setting('app.current_org_id')::UUID);
```
在使用此策略时，应用程序在数据库会话连接初始化后，必须设置 `app.current_org_id` 变量。

## 5. Token 用量统计与配额系统

为了支撑 SaaS 的成本控制与商业化，必须对大模型的调用进行严密的追踪和配额限制。

### 5.1 数据追踪 (Usage Tracking)

*   **精确记录**：每次调用大模型（包括文本对话 `chat` 和向量化 `embedding`），必须解析返回的 `usage` 元数据，将 `model`、`prompt_tokens`、`completion_tokens` 以及计算出的真实货币 `cost` 存入 `usage_logs` 表。
*   **成本计算**：后端维护模型价格表，动态计算 `cost = (prompt_tokens * input_rate) + (completion_tokens * output_rate)`。

### 5.2 组织配额限制 (Quota Limiting)

组织表 (`organizations`) 需扩展配额管控字段（或通过 Redis 等缓存层实现）：
*   **限制逻辑**：用户发起对话或上传文档前，系统拦截请求校验当前组织本周期内累计消耗的 Token 数是否超过允许的额度。
*   **异步更新**：高并发下，为了避免竞争条件，系统响应用户后，采用异步机制（或消息队列）累加组织的 `quota_tokens_used`。

## 6. 开发者 API 接入体系

为允许租户将我们的 AI 系统集成到他们的业务中，系统提供标准的 API 接入能力。

### 6.1 鉴权与安全
1.  **密钥生成**：租户在控制台生成 API Key。系统生成完整的 `sk_xxxx` 并仅在页面展示一次。数据库中存储其哈希值 `key_hash` 和前缀 `key_prefix` 以备展示。
2.  **API 鉴权**：客户端请求携带 `Authorization: Bearer sk_xxxx`。API 网关拦截请求，哈希处理后与 `api_keys` 表进行匹配，并解析出对应的 `org_id` 上下文。

### 6.2 高性能限流 (Rate Limiting)
引入 **Redis** 用于 API 请求的限流控制：
*   **QPS 控制**：依据 `api_keys.qps_limit` 字段，在 Redis 中使用令牌桶 (Token Bucket) 或固定窗口算法进行高频拦截，防止恶意刷接口。
*   **双层配额校验**：不仅校验 `api_keys.token_quota`，还要校验顶层 `organizations.quota_tokens_limit`，任一超限即返回 429 (Too Many Requests) 或 402 (Payment Required)。

## 7. 用户系统与权限模型

为了支持企业内部团队的协作和数据共享，系统建立在多租户（Organization）基础之上，并包含完善的基于角色（RBAC）的权限控制和邀请机制。

### 5.1 权限角色 (Role) 定义

在 `organization_users` 表中定义 4 种标准角色：

*   **Owner (所有者)**：最高权限，创建组织时的默认角色。可管理计费、删除组织、转让所有权以及包含 Admin 的所有权限。
*   **Admin (管理员)**：可邀请/移除成员、修改成员角色、管理系统集成（如配置 API Keys 等）。
*   **Member (普通成员)**：核心业务使用者。可上传、管理自己所在组织的知识库（Documents）、发起 AI 对话。
*   **Viewer (观察者/只读)**：仅允许查询和对话。不能上传文件，也不能修改配置。适用于组织内只需查阅知识库的普通员工。

### 5.2 邀请机制 (Invitation Flow)

新增一张 `organization_invitations` 表，支持通过邮箱邀请尚未注册的用户加入组织：

1. Admin 指定邮箱并选择角色（如 `Viewer`）发出邀请。
2. 系统生成唯一 Token 链接，并存入邀请表，设置有效期。
3. 接收者点击链接后，若未注册则引导注册，注册/登录后消费该 Token，自动加入对应组织并分配角色。

### 5.3 认证与授权 (Authentication & Authorization)

*   **认证 (AuthN)**：采用 JWT (JSON Web Token)，用户登录后发放，包含 `user_id` 等信息。
*   **授权 (AuthZ)**：客户端请求时需携带 `Authorization: Bearer <token>`，同时通过自定义 Header `X-Organization-Id` 表明当前操作所在的组织。后端通过中间件拦截请求，校验 JWT，并实时查库确认该用户在对应 `org_id` 下的角色是否有权限执行当前路由操作。

### 5.4 数据模型补充 (SQL)

```sql
-- 修改 organization_users 的角色约束
ALTER TABLE organization_users 
ADD CONSTRAINT chk_role CHECK (role IN ('owner', 'admin', 'member', 'viewer'));

-- 新增：邀请表
CREATE TABLE organization_invitations (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    inviter_id UUID REFERENCES users(id),
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) CHECK (role IN ('admin', 'member', 'viewer')),
    token VARCHAR(255) UNIQUE NOT NULL, -- 用于生成邀请链接
    status VARCHAR(50) DEFAULT 'pending', -- pending, accepted, expired
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
