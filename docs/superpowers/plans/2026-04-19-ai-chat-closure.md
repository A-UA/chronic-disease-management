# AI 问答模块闭环修复 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AI 问答模块从内存原型升级为生产闭环系统——持久化会话、多租户隔离、向量清理、引用透传。

**Architecture:** 新建 `ai-service` (TCP :8031) 承载知识库+会话+消息；Gateway 删除内存 Map 改为 TCP 调用；Agent 新增删除 API、多格式解析、Artifact 引用。

**Tech Stack:** NestJS 11 / TypeORM 0.3 / LangGraph / LangChain Core / FastAPI / PostgreSQL / Milvus

---

## 文件结构

### 新建文件
| 文件 | 职责 |
|------|------|
| `database/init.sql` (追加) | 新增 conversations + chat_messages 表 |
| `backend-nestjs/libs/shared/src/dto/ai.dto.ts` | AI 服务入站 DTO |
| `backend-nestjs/libs/shared/src/vo/ai.vo.ts` | AI 服务出站 VO |
| `backend-nestjs/apps/ai/package.json` | ai-service 包配置 |
| `backend-nestjs/apps/ai/tsconfig.json` | ai-service TS 配置 |
| `backend-nestjs/apps/ai/nest-cli.json` | ai-service NestCLI 配置 |
| `backend-nestjs/apps/ai/src/main.ts` | ai-service TCP 启动 |
| `backend-nestjs/apps/ai/src/app.module.ts` | ai-service 根模块 |
| `backend-nestjs/apps/ai/src/knowledge/` | 从 patient-service 迁入（6 文件） |
| `backend-nestjs/apps/ai/src/conversation/entities/conversation.entity.ts` | 会话实体 |
| `backend-nestjs/apps/ai/src/conversation/entities/chat-message.entity.ts` | 消息实体 |
| `backend-nestjs/apps/ai/src/conversation/conversation.service.ts` | 会话业务逻辑 |
| `backend-nestjs/apps/ai/src/conversation/conversation.controller.ts` | TCP 消息处理器 |
| `backend-nestjs/apps/ai/src/conversation/conversation.module.ts` | 会话模块 |

### 修改文件
| 文件 | 变更 |
|------|------|
| `backend-nestjs/libs/shared/src/constants.ts` | 新增 AI_SERVICE 常量 |
| `backend-nestjs/libs/shared/src/dto/index.ts` | 导出 ai.dto |
| `backend-nestjs/libs/shared/src/vo/index.ts` | 导出 ai.vo |
| `backend-nestjs/apps/patient/src/app.module.ts` | 移除 KnowledgeModule |
| `backend-nestjs/package.json` | 新增 dev:ai 脚本 |
| `backend-nestjs/apps/gateway/src/app.module.ts` | 注册 AI_SERVICE 客户端 |
| `backend-nestjs/apps/gateway/src/proxy/knowledge-base-proxy.controller.ts` | PATIENT→AI 路由 |
| `backend-nestjs/apps/gateway/src/proxy/knowledge-document-proxy.controller.ts` | PATIENT→AI 路由 + 删除联动 |
| `backend-nestjs/apps/gateway/src/proxy/chat-proxy.controller.ts` | 传递 identity 上下文 |
| `backend-nestjs/apps/gateway/src/proxy/services/agent-proxy.service.ts` | 核心重构 |
| `agent/pyproject.toml` | 新增 pypdf/docx2txt/langchain-community |
| `agent/app/agent/graph.py` | trim_messages + async |
| `agent/app/agent/tools/rag_tool.py` | Artifact 引用 + 注入修复 |
| `agent/app/agent/ingestion.py` | 多格式解析 |
| `agent/app/routers/internal.py` | 新增向量删除端点 + SSE artifact |

---

## Task 1: 数据库 Schema — 新增会话表

**Files:**
- Modify: `database/init.sql:267` (在 documents 表后追加)

- [ ] **Step 1: 在 init.sql 末尾（种子数据前）追加建表语句**

在 `documents` 索引之后（第 267 行），`第二部分：种子数据` 注释之前，插入：

```sql
-- -----------------------------------------------------------
-- 17. conversations - 会话表
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
-- 18. chat_messages - 聊天消息表
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

- [ ] **Step 2: 在本地 PostgreSQL 执行建表验证**

```powershell
psql -h localhost -U postgres -d cdm -c "
CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kb_id BIGINT REFERENCES knowledge_bases(id) ON DELETE SET NULL,
    title VARCHAR(100) NOT NULL DEFAULT '新对话',
    message_count INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    last_message_at TIMESTAMP NOT NULL DEFAULT now(),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB,
    metadata JSONB,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP
);
"
```
Expected: `CREATE TABLE` ×2，无错误。

- [ ] **Step 3: 提交**

```powershell
git add database/init.sql
git commit -m "数据库: 新增 conversations 和 chat_messages 表"
```

---

## Task 2: 共享库 — 新增 AI 服务常量、DTO、VO

**Files:**
- Modify: `backend-nestjs/libs/shared/src/constants.ts`
- Create: `backend-nestjs/libs/shared/src/dto/ai.dto.ts`
- Create: `backend-nestjs/libs/shared/src/vo/ai.vo.ts`
- Modify: `backend-nestjs/libs/shared/src/dto/index.ts`
- Modify: `backend-nestjs/libs/shared/src/vo/index.ts`

- [ ] **Step 1: 更新 constants.ts — 新增 AI 服务常量**

将 `constants.ts` 整体替换为：

```typescript
export const AUTH_SERVICE = 'AUTH_SERVICE';
export const PATIENT_SERVICE = 'PATIENT_SERVICE';
export const AI_SERVICE = 'AI_SERVICE';

export const AUTH_TCP_PORT = 8011;
export const PATIENT_TCP_PORT = 8021;
export const AI_TCP_PORT = 8031;

// 知识库命令（迁移至 ai-service）
export const KNOWLEDGE_BASE_FIND_ALL = 'kb_find_all';
export const KNOWLEDGE_BASE_CREATE = 'kb_create';
export const KNOWLEDGE_BASE_STATS = 'kb_stats';
export const KNOWLEDGE_BASE_DELETE = 'kb_delete';

export const DOCUMENT_FIND_BY_KB = 'document_find_by_kb';
export const DOCUMENT_CREATE_SYNC = 'document_create_sync';
export const DOCUMENT_DELETE = 'document_delete';
export const DOCUMENT_FIND_ONE = 'document_find_one';

// 会话命令
export const CONVERSATION_FIND_ALL = 'conv_find_all';
export const CONVERSATION_FIND_ONE = 'conv_find_one';
export const CONVERSATION_CREATE = 'conv_create';
export const CONVERSATION_DELETE = 'conv_delete';
export const MESSAGE_CREATE = 'msg_create';

// 知识库归属校验
export const KB_VERIFY_OWNERSHIP = 'kb_verify_ownership';
```

注意：删除了 `CHAT_SERVICE` 和 `CHAT_TCP_PORT`（原有但未使用），合并为 `AI_SERVICE`。

- [ ] **Step 2: 创建 ai.dto.ts**

```typescript
// backend-nestjs/libs/shared/src/dto/ai.dto.ts
import type { IdentityPayload } from '../interfaces/identity.interface.js';

// ─── AI 微服务 TCP 消息载荷 ───

/** 创建会话 */
export interface CreateConversationPayload {
  identity: IdentityPayload;
  kbId?: string;
  title?: string;
}

/** 查询会话 */
export interface ConversationIdPayload {
  identity: IdentityPayload;
  id: string;
}

/** 创建消息 */
export interface CreateMessagePayload {
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: CitationData[];
  metadata?: Record<string, unknown>;
  tokenCount?: number;
}

/** 引用数据结构 */
export interface CitationData {
  ref: string;
  source: string;
  snippet: string;
  page?: number;
}

/** KB 归属校验 */
export interface KbVerifyOwnershipPayload {
  kbId: string;
  tenantId: string;
}
```

- [ ] **Step 3: 创建 ai.vo.ts**

```typescript
// backend-nestjs/libs/shared/src/vo/ai.vo.ts

// ─── AI 域出站视图对象 ───

/** 会话视图 */
export interface ConversationVO {
  id: string;
  tenantId: string;
  orgId: string;
  userId: string;
  kbId: string | null;
  title: string;
  messageCount: number;
  totalTokens: number;
  lastMessageAt: Date;
  createdAt: Date;
}

/** 会话详情视图（含消息列表） */
export interface ConversationDetailVO extends ConversationVO {
  messages: ChatMessageVO[];
}

/** 聊天消息视图 */
export interface ChatMessageVO {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations: CitationVO[] | null;
  metadata: Record<string, unknown> | null;
  tokenCount: number;
  createdAt: Date;
}

/** 引用视图 */
export interface CitationVO {
  ref: string;
  source: string;
  snippet: string;
  page?: number;
}

/** KB 归属校验结果 */
export interface KbOwnershipResultVO {
  valid: boolean;
  kbId: string;
  tenantId: string;
}
```

- [ ] **Step 4: 更新 dto/index.ts 和 vo/index.ts**

`dto/index.ts` 追加一行：
```typescript
export * from './ai.dto.js';
```

`vo/index.ts` 追加一行：
```typescript
export * from './ai.vo.js';
```

- [ ] **Step 5: 迁移知识库 DTO — 从 patient.dto.ts 剥离**

从 `patient.dto.ts` 中**剪切**第 50-84 行（`// ─── 知识库 TCP 消息载荷 ───` 及以下 6 个 interface），**粘贴**到 `ai.dto.ts` 的底部。`patient.dto.ts` 中不再保留这些接口。

`ai.dto.ts` 末尾追加：

```typescript
// ─── 知识库 TCP 消息载荷（从 patient.dto.ts 迁入） ───

export interface CreateKbPayload {
  identity: IdentityPayload;
  data: CreateKbData;
}

export interface CreateKbData {
  name: string;
  description?: string;
}

export interface KbIdPayload {
  identity: IdentityPayload;
  id: string;
}

export interface DocsByKbPayload {
  kbId: string;
}

export interface SyncDocumentPayload {
  identity: IdentityPayload;
  kbId: string;
  fileName: string;
  fileType?: string;
  fileSize?: number;
  minioUrl: string;
  chunkCount?: number;
  status?: string;
}

export interface DeleteDocPayload {
  id: string;
}
```

同时将 `patient.vo.ts` 中的 `KnowledgeBaseVO`、`KnowledgeBaseStatsVO`、`DocumentVO`、`DocumentSyncResultVO`（第 51-87 行）剪切到 `ai.vo.ts`。

- [ ] **Step 6: 验证编译**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm run build --filter=@cdm/shared
```
Expected: 编译成功，无类型错误。

- [ ] **Step 7: 提交**

```powershell
git add libs/shared/
git commit -m "共享库: 新增 AI 服务常量/DTO/VO，迁移知识库类型定义"
```

---

## Task 3: ai-service 脚手架 — 创建微服务骨架

**Files:**
- Create: `backend-nestjs/apps/ai/package.json`
- Create: `backend-nestjs/apps/ai/tsconfig.json`
- Create: `backend-nestjs/apps/ai/nest-cli.json`
- Create: `backend-nestjs/apps/ai/src/main.ts`
- Create: `backend-nestjs/apps/ai/src/app.module.ts`
- Modify: `backend-nestjs/package.json` (新增 dev:ai 脚本)

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "@cdm/ai",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "nest build",
    "dev": "nest start --watch",
    "start:prod": "node dist/main",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:cov": "jest --coverage"
  },
  "dependencies": {
    "@cdm/shared": "workspace:*",
    "@nestjs/common": "catalog:",
    "@nestjs/core": "catalog:",
    "@nestjs/config": "catalog:",
    "@nestjs/microservices": "catalog:",
    "@nestjs/typeorm": "catalog:",
    "pg": "catalog:",
    "reflect-metadata": "catalog:",
    "rxjs": "catalog:",
    "typeorm": "catalog:"
  },
  "devDependencies": {
    "@nestjs/cli": "catalog:",
    "@nestjs/schematics": "catalog:",
    "@nestjs/testing": "catalog:",
    "@types/jest": "catalog:",
    "@types/node": "catalog:",
    "jest": "catalog:",
    "ts-jest": "catalog:",
    "typescript": "catalog:"
  },
  "jest": {
    "moduleFileExtensions": ["js", "json", "ts"],
    "rootDir": "src",
    "testRegex": ".*\\.spec\\.ts$",
    "transform": { "^.+\\.(t|j)s$": "ts-jest" },
    "collectCoverageFrom": ["**/*.(t|j)s"],
    "coverageDirectory": "../coverage",
    "testEnvironment": "node"
  }
}
```

- [ ] **Step 2: 创建 tsconfig.json**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: 创建 nest-cli.json**

```json
{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "deleteOutDir": true
  }
}
```

- [ ] **Step 4: 创建 main.ts**

```typescript
// backend-nestjs/apps/ai/src/main.ts
import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module.js';
import { AI_TCP_PORT } from '@cdm/shared';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.TCP,
    options: {
      host: '0.0.0.0',
      port: Number(process.env.AI_TCP_PORT) || AI_TCP_PORT,
    },
  });
  await app.listen();
  console.log(`AI service listening on TCP port ${AI_TCP_PORT}`);
}
bootstrap();
```

- [ ] **Step 5: 创建 app.module.ts（先只含数据库连接，后续 Task 填充模块）**

```typescript
// backend-nestjs/apps/ai/src/app.module.ts
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { databaseConfig } from '@cdm/shared';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [databaseConfig] }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host: config.get<string>('database.host'),
        port: config.get<number>('database.port'),
        username: config.get<string>('database.username'),
        password: config.get<string>('database.password'),
        database: config.get<string>('database.database'),
        autoLoadEntities: true,
        synchronize: false,
      }),
    }),
  ],
})
export class AppModule {}
```

- [ ] **Step 6: 更新根 package.json — 新增 dev:ai 脚本**

在 `backend-nestjs/package.json` 的 `scripts` 中新增一行：

```json
"dev:ai": "turbo run dev --filter=@cdm/ai",
```

- [ ] **Step 7: 安装依赖并验证编译**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm install
pnpm run build --filter=@cdm/ai
```
Expected: 安装成功，编译成功。

- [ ] **Step 8: 提交**

```powershell
git add apps/ai/ package.json pnpm-lock.yaml
git commit -m "基础设施: 创建 ai-service 微服务骨架"
```

---

## Task 4: 知识库模块迁移 — patient → ai

**Files:**
- Copy: `backend-nestjs/apps/patient/src/knowledge/` → `backend-nestjs/apps/ai/src/knowledge/`
- Modify: `backend-nestjs/apps/patient/src/app.module.ts` (移除 KnowledgeModule)
- Modify: `backend-nestjs/apps/ai/src/app.module.ts` (导入 KnowledgeModule)

- [ ] **Step 1: 复制 knowledge 目录到 ai-service**

```powershell
Copy-Item -Recurse d:\codes\chronic-disease-management\backend-nestjs\apps\patient\src\knowledge d:\codes\chronic-disease-management\backend-nestjs\apps\ai\src\knowledge
```

- [ ] **Step 2: 更新 ai-service 的 knowledge.service.ts 导入路径**

文件: `backend-nestjs/apps/ai/src/knowledge/knowledge.service.ts`

将 `import type { ... } from '@cdm/shared';` 中的类型引用更新——由于知识库 DTO/VO 已迁至 `ai.dto.ts` / `ai.vo.ts`，但仍从 `@cdm/shared` 的统一入口导出，故**无需修改导入路径**。只需确认编译通过。

- [ ] **Step 3: 更新 knowledge.controller.ts 增加 KB_VERIFY_OWNERSHIP 和 DOCUMENT_FIND_ONE**

文件: `backend-nestjs/apps/ai/src/knowledge/knowledge.controller.ts`

在已有的 `@MessagePattern` 之后追加：

```typescript
@MessagePattern({ cmd: KB_VERIFY_OWNERSHIP })
verifyKbOwnership(@Payload() payload: KbVerifyOwnershipPayload) {
  return this.service.verifyKbOwnership(payload.kbId, payload.tenantId);
}

@MessagePattern({ cmd: DOCUMENT_FIND_ONE })
findOneDoc(@Payload() payload: DeleteDocPayload) {
  return this.service.findOneDoc(payload.id);
}
```

同时更新 imports 引入 `KB_VERIFY_OWNERSHIP`、`DOCUMENT_FIND_ONE`、`KbVerifyOwnershipPayload`。

- [ ] **Step 4: 在 knowledge.service.ts 新增 verifyKbOwnership 和 findOneDoc**

```typescript
async verifyKbOwnership(kbId: string, tenantId: string): Promise<KbOwnershipResultVO> {
  const kb = await this.kbRepo.findOne({ where: { id: kbId, tenantId } });
  return { valid: !!kb, kbId, tenantId };
}

async findOneDoc(id: string): Promise<DocumentVO | null> {
  const doc = await this.docRepo.findOne({ where: { id } });
  return doc ? KnowledgeService.toDocVO(doc) : null;
}
```

同时更新 imports 引入 `KbOwnershipResultVO`。

- [ ] **Step 5: 更新 ai-service app.module.ts 导入 KnowledgeModule**

```typescript
import { KnowledgeModule } from './knowledge/knowledge.module.js';

@Module({
  imports: [
    // ... 已有的 ConfigModule, TypeOrmModule ...
    KnowledgeModule,
  ],
})
export class AppModule {}
```

- [ ] **Step 6: 从 patient-service 移除 KnowledgeModule**

文件: `backend-nestjs/apps/patient/src/app.module.ts`

删除 `import { KnowledgeModule } from './knowledge/knowledge.module.js';` 以及 imports 数组中的 `KnowledgeModule`。

- [ ] **Step 7: 删除 patient-service 中的 knowledge 目录**

```powershell
Remove-Item -Recurse d:\codes\chronic-disease-management\backend-nestjs\apps\patient\src\knowledge
```

- [ ] **Step 8: 验证两个服务编译**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm run build --filter=@cdm/ai
pnpm run build --filter=@cdm/patient
```
Expected: 两者均编译成功。

- [ ] **Step 9: 提交**

```powershell
git add apps/ai/src/knowledge/ apps/patient/src/ apps/ai/src/app.module.ts
git commit -m "重构: 将知识库模块从 patient-service 迁移至 ai-service"
```

---

## Task 5: 会话模块 — Entity + Service + Controller

**Files:**
- Create: `backend-nestjs/apps/ai/src/conversation/entities/conversation.entity.ts`
- Create: `backend-nestjs/apps/ai/src/conversation/entities/chat-message.entity.ts`
- Create: `backend-nestjs/apps/ai/src/conversation/conversation.service.ts`
- Create: `backend-nestjs/apps/ai/src/conversation/conversation.controller.ts`
- Create: `backend-nestjs/apps/ai/src/conversation/conversation.module.ts`
- Modify: `backend-nestjs/apps/ai/src/app.module.ts`

- [ ] **Step 1: 创建 conversation.entity.ts**

```typescript
// backend-nestjs/apps/ai/src/conversation/entities/conversation.entity.ts
import { Entity, Column, PrimaryColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('conversations')
export class ConversationEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @Column({ name: 'user_id', type: 'bigint' })
  userId: string;

  @Column({ name: 'kb_id', type: 'bigint', nullable: true })
  kbId: string | null;

  @Column({ length: 100, default: '新对话' })
  title: string;

  @Column({ name: 'message_count', type: 'int', default: 0 })
  messageCount: number;

  @Column({ name: 'total_tokens', type: 'int', default: 0 })
  totalTokens: number;

  @Column({ name: 'last_message_at', type: 'timestamp', default: () => 'now()' })
  lastMessageAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
```

- [ ] **Step 2: 创建 chat-message.entity.ts**

```typescript
// backend-nestjs/apps/ai/src/conversation/entities/chat-message.entity.ts
import { Entity, Column, PrimaryColumn, CreateDateColumn } from 'typeorm';

@Entity('chat_messages')
export class ChatMessageEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'conversation_id', type: 'bigint' })
  conversationId: string;

  @Column({ length: 20 })
  role: 'user' | 'assistant' | 'system';

  @Column({ type: 'text' })
  content: string;

  @Column({ type: 'jsonb', nullable: true })
  citations: Record<string, unknown>[] | null;

  @Column({ type: 'jsonb', nullable: true })
  metadata: Record<string, unknown> | null;

  @Column({ name: 'token_count', type: 'int', default: 0 })
  tokenCount: number;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
```

- [ ] **Step 3: 创建 conversation.service.ts**

```typescript
// backend-nestjs/apps/ai/src/conversation/conversation.service.ts
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { ConversationEntity } from './entities/conversation.entity.js';
import { ChatMessageEntity } from './entities/chat-message.entity.js';
import { nextId } from '@cdm/shared';
import type {
  ConversationVO,
  ConversationDetailVO,
  ChatMessageVO,
} from '@cdm/shared';

@Injectable()
export class ConversationService {
  constructor(
    @InjectRepository(ConversationEntity) private convRepo: Repository<ConversationEntity>,
    @InjectRepository(ChatMessageEntity) private msgRepo: Repository<ChatMessageEntity>,
    private dataSource: DataSource,
  ) {}

  async findAll(tenantId: string, userId: string): Promise<ConversationVO[]> {
    const entities = await this.convRepo.find({
      where: { tenantId, userId },
      order: { lastMessageAt: 'DESC' },
    });
    return entities.map(ConversationService.toConvVO);
  }

  async findOne(id: string, tenantId: string, userId: string): Promise<ConversationDetailVO | null> {
    const conv = await this.convRepo.findOne({ where: { id, tenantId, userId } });
    if (!conv) return null;

    const messages = await this.msgRepo.find({
      where: { conversationId: id },
      order: { createdAt: 'ASC' },
    });

    return {
      ...ConversationService.toConvVO(conv),
      messages: messages.map(ConversationService.toMsgVO),
    };
  }

  async create(tenantId: string, orgId: string, userId: string, kbId?: string, title?: string): Promise<ConversationVO> {
    const conv = this.convRepo.create({
      id: nextId(),
      tenantId,
      orgId,
      userId,
      kbId: kbId ?? null,
      title: title ?? '新对话',
    });
    const saved = await this.convRepo.save(conv);
    return ConversationService.toConvVO(saved);
  }

  async delete(id: string, tenantId: string, userId: string): Promise<{ affected: number }> {
    const result = await this.convRepo.delete({ id, tenantId, userId });
    return { affected: result.affected ?? 0 };
  }

  async createMessage(
    conversationId: string,
    role: 'user' | 'assistant' | 'system',
    content: string,
    citations?: Record<string, unknown>[],
    metadata?: Record<string, unknown>,
    tokenCount?: number,
  ): Promise<ChatMessageVO> {
    const tc = tokenCount ?? 0;

    return this.dataSource.transaction(async (manager) => {
      const msg = manager.create(ChatMessageEntity, {
        id: nextId(),
        conversationId,
        role,
        content,
        citations: citations ?? null,
        metadata: metadata ?? null,
        tokenCount: tc,
      });
      const saved = await manager.save(msg);

      // 更新会话统计
      await manager.increment(ConversationEntity, { id: conversationId }, 'messageCount', 1);
      await manager.increment(ConversationEntity, { id: conversationId }, 'totalTokens', tc);
      await manager.update(ConversationEntity, { id: conversationId }, { lastMessageAt: new Date() });

      return ConversationService.toMsgVO(saved);
    });
  }

  static toConvVO(entity: ConversationEntity): ConversationVO {
    return {
      id: entity.id,
      tenantId: entity.tenantId,
      orgId: entity.orgId,
      userId: entity.userId,
      kbId: entity.kbId,
      title: entity.title,
      messageCount: entity.messageCount,
      totalTokens: entity.totalTokens,
      lastMessageAt: entity.lastMessageAt,
      createdAt: entity.createdAt,
    };
  }

  static toMsgVO(entity: ChatMessageEntity): ChatMessageVO {
    return {
      id: entity.id,
      conversationId: entity.conversationId,
      role: entity.role,
      content: entity.content,
      citations: entity.citations as ChatMessageVO['citations'],
      metadata: entity.metadata,
      tokenCount: entity.tokenCount,
      createdAt: entity.createdAt,
    };
  }
}
```

- [ ] **Step 4: 创建 conversation.controller.ts**

```typescript
// backend-nestjs/apps/ai/src/conversation/conversation.controller.ts
import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { ConversationService } from './conversation.service.js';
import {
  CONVERSATION_FIND_ALL, CONVERSATION_FIND_ONE,
  CONVERSATION_CREATE, CONVERSATION_DELETE,
  MESSAGE_CREATE,
} from '@cdm/shared';
import type {
  IdentityPayload,
  CreateConversationPayload,
  ConversationIdPayload,
  CreateMessagePayload,
} from '@cdm/shared';

@Controller()
export class ConversationController {
  constructor(private readonly service: ConversationService) {}

  @MessagePattern({ cmd: CONVERSATION_FIND_ALL })
  findAll(@Payload() identity: IdentityPayload) {
    return this.service.findAll(identity.tenantId, identity.userId);
  }

  @MessagePattern({ cmd: CONVERSATION_FIND_ONE })
  findOne(@Payload() payload: ConversationIdPayload) {
    return this.service.findOne(payload.id, payload.identity.tenantId, payload.identity.userId);
  }

  @MessagePattern({ cmd: CONVERSATION_CREATE })
  create(@Payload() payload: CreateConversationPayload) {
    return this.service.create(
      payload.identity.tenantId,
      payload.identity.orgId,
      payload.identity.userId,
      payload.kbId,
      payload.title,
    );
  }

  @MessagePattern({ cmd: CONVERSATION_DELETE })
  delete(@Payload() payload: ConversationIdPayload) {
    return this.service.delete(payload.id, payload.identity.tenantId, payload.identity.userId);
  }

  @MessagePattern({ cmd: MESSAGE_CREATE })
  createMessage(@Payload() payload: CreateMessagePayload) {
    return this.service.createMessage(
      payload.conversationId,
      payload.role,
      payload.content,
      payload.citations,
      payload.metadata,
      payload.tokenCount,
    );
  }
}
```

- [ ] **Step 5: 创建 conversation.module.ts**

```typescript
// backend-nestjs/apps/ai/src/conversation/conversation.module.ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConversationEntity } from './entities/conversation.entity.js';
import { ChatMessageEntity } from './entities/chat-message.entity.js';
import { ConversationController } from './conversation.controller.js';
import { ConversationService } from './conversation.service.js';

@Module({
  imports: [TypeOrmModule.forFeature([ConversationEntity, ChatMessageEntity])],
  controllers: [ConversationController],
  providers: [ConversationService],
})
export class ConversationModule {}
```

- [ ] **Step 6: 更新 app.module.ts 导入 ConversationModule**

```typescript
import { KnowledgeModule } from './knowledge/knowledge.module.js';
import { ConversationModule } from './conversation/conversation.module.js';

@Module({
  imports: [
    // ... ConfigModule, TypeOrmModule ...
    KnowledgeModule,
    ConversationModule,
  ],
})
export class AppModule {}
```

- [ ] **Step 7: 验证编译**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm run build --filter=@cdm/ai
```
Expected: 编译成功。

- [ ] **Step 8: 提交**

```powershell
git add apps/ai/src/conversation/ apps/ai/src/app.module.ts
git commit -m "功能: 实现会话+消息 CRUD（ai-service）"
```

---

## Task 6: Gateway — 注册 AI 客户端 + 路由迁移

**Files:**
- Modify: `backend-nestjs/apps/gateway/src/app.module.ts`
- Modify: `backend-nestjs/apps/gateway/src/proxy/knowledge-base-proxy.controller.ts`
- Modify: `backend-nestjs/apps/gateway/src/proxy/knowledge-document-proxy.controller.ts`

- [ ] **Step 1: app.module.ts — 注册 AI_SERVICE 客户端**

在 `ClientsModule.register` 数组中新增第三个客户端：

```typescript
{
  name: AI_SERVICE,
  transport: Transport.TCP,
  options: { host: process.env.AI_HOST || 'localhost', port: Number(process.env.AI_TCP_PORT) || AI_TCP_PORT },
},
```

同时更新 import：`import { BigIntSerializerInterceptor, AUTH_TCP_PORT, PATIENT_TCP_PORT, AI_TCP_PORT, AI_SERVICE } from '@cdm/shared';`

- [ ] **Step 2: knowledge-base-proxy.controller.ts — PATIENT→AI 路由**

将 `@Inject(PATIENT_SERVICE)` 改为 `@Inject(AI_SERVICE)`，对应 import 更新：

```typescript
import { AI_SERVICE, KNOWLEDGE_BASE_FIND_ALL, ... } from '@cdm/shared';

export class KnowledgeBaseProxyController {
  constructor(@Inject(AI_SERVICE) private readonly aiClient: ClientProxy) {}

  @Get()
  findAll(@CurrentUser() identity: IdentityPayload) {
    return this.aiClient.send({ cmd: KNOWLEDGE_BASE_FIND_ALL }, identity);
  }
  // ... 其他方法同理，将 patientClient 改为 aiClient
}
```

- [ ] **Step 3: knowledge-document-proxy.controller.ts — PATIENT→AI 路由**

同 Step 2，将 `@Inject(PATIENT_SERVICE)` 改为 `@Inject(AI_SERVICE)`。所有 `this.patientClient.send(...)` 改为 `this.aiClient.send(...)`。

- [ ] **Step 4: 验证编译**

```powershell
pnpm run build --filter=@cdm/gateway
```
Expected: 编译成功。

- [ ] **Step 5: 提交**

```powershell
git add apps/gateway/
git commit -m "重构: Gateway 知识库路由从 patient-service 切换至 ai-service"
```

---

## Task 7: Gateway — AgentProxyService 核心重构

**Files:**
- Modify: `backend-nestjs/apps/gateway/src/proxy/services/agent-proxy.service.ts`
- Modify: `backend-nestjs/apps/gateway/src/proxy/chat-proxy.controller.ts`

- [ ] **Step 1: AgentProxyService — 删除内存 Map，注入 AI_SERVICE 客户端**

完整重写 `agent-proxy.service.ts`。核心变更：
- 删除 `private conversations = new Map<>()`
- 注入 `@Inject(AI_SERVICE) private aiClient: ClientProxy`
- 会话 CRUD 改为 TCP 转发
- `streamChat` 增加 KB 校验 + 消息持久化 + SSE 事件透传

注意：这是整个重构中最大的文件变更。完整代码请参照设计规格书 Section 5 实现。关键变更点：

1. 构造函数注入 `aiClient: ClientProxy`
2. `getConversations(identity)` → `this.aiClient.send({ cmd: CONVERSATION_FIND_ALL }, identity)`
3. `getConversation(id, identity)` → `this.aiClient.send({ cmd: CONVERSATION_FIND_ONE }, { identity, id })`
4. `deleteConversation(id, identity)` → `this.aiClient.send({ cmd: CONVERSATION_DELETE }, { identity, id })`
5. `streamChat(identity, query, kbId, conversationId, res)`:
   - Step 2-3: KB 校验 + 创建会话
   - Step 4: 保存用户消息
   - Step 5: 获取历史
   - Step 6-7: 调用 Agent + SSE 转发（新增 tool_start/tool_end/citations/error 事件解析）
   - Step 8: 保存 assistant 消息

- [ ] **Step 2: chat-proxy.controller.ts — 传递完整 identity**

更新 `ConversationProxyController` 和 `ChatProxyController`，将 `IdentityPayload` 传递给所有 AgentProxyService 方法（取代原来的 `userId`）：

```typescript
@Controller('conversations')
@UseGuards(JwtAuthGuard)
export class ConversationProxyController {
  constructor(private readonly agentService: AgentProxyService) {}

  @Get()
  getConversations(@CurrentUser() identity: IdentityPayload) {
    return this.agentService.getConversations(identity);
  }

  @Get(':id')
  getConversation(@Param('id') id: string, @CurrentUser() identity: IdentityPayload) {
    return this.agentService.getConversation(id, identity);
  }

  @Delete(':id')
  deleteConversation(@Param('id') id: string, @CurrentUser() identity: IdentityPayload) {
    return this.agentService.deleteConversation(id, identity);
  }
}

@Controller('chat')
@UseGuards(JwtAuthGuard)
export class ChatProxyController {
  constructor(private readonly agentService: AgentProxyService) {}

  @Post()
  async sendChat(
    @Body() body: { kb_id: string; query: string; conversation_id?: string },
    @CurrentUser() identity: IdentityPayload,
    @Res() res: Response,
  ) {
    await this.agentService.streamChat(identity, body.query, body.kb_id, body.conversation_id, res);
  }
}
```

- [ ] **Step 3: 验证编译**

```powershell
pnpm run build --filter=@cdm/gateway
```
Expected: 编译成功。

- [ ] **Step 4: 提交**

```powershell
git add apps/gateway/src/proxy/
git commit -m "重构: AgentProxyService 删除内存 Map，改为 TCP 持久化 + SSE 事件透传"
```

---

## Task 8: Agent — 向量删除 API + 多格式解析

**Files:**
- Modify: `agent/app/routers/internal.py`
- Modify: `agent/app/agent/ingestion.py`
- Modify: `agent/pyproject.toml`

- [ ] **Step 1: 新增 Python 依赖**

在 `pyproject.toml` 的 `dependencies` 中追加：

```toml
    "langchain-community>=0.3.0",
    "pypdf>=5.0.0",
    "docx2txt>=0.9",
```

- [ ] **Step 2: 安装依赖**

```powershell
cd d:\codes\chronic-disease-management\agent
uv sync
```
Expected: 安装成功。

- [ ] **Step 3: 重写 ingestion.py — 多格式解析**

```python
# agent/app/agent/ingestion.py
import tempfile
import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from app.config import settings


def _load_documents(file_bytes: bytes, filename: str) -> list[Document]:
    """根据文件扩展名选择合适的 Loader。"""
    ext = Path(filename).suffix.lower()

    if ext in ('.txt', '.md'):
        text = file_bytes.decode('utf-8', errors='ignore')
        return [Document(page_content=text, metadata={"filename": filename, "source": filename})]

    if ext == '.pdf':
        from langchain_community.document_loaders import PyPDFLoader
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            loader = PyPDFLoader(tmp_path)
            docs = loader.load()
            for doc in docs:
                doc.metadata["filename"] = filename
                doc.metadata["source"] = filename
            return docs
        finally:
            os.unlink(tmp_path)

    if ext == '.docx':
        from langchain_community.document_loaders import Docx2txtLoader
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            loader = Docx2txtLoader(tmp_path)
            docs = loader.load()
            for doc in docs:
                doc.metadata["filename"] = filename
                doc.metadata["source"] = filename
            return docs
        finally:
            os.unlink(tmp_path)

    raise ValueError(f"不支持的文件格式: {ext}（支持 .txt, .md, .pdf, .docx）")


def _get_vector_store() -> Milvus:
    """获取 Milvus 向量存储实例。"""
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )
    return Milvus(
        embedding_function=embeddings,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,
    )


def process_document_to_milvus(file_bytes: bytes, filename: str, kb_id: str) -> int:
    raw_docs = _load_documents(file_bytes, filename)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs: list[Document] = []
    for raw in raw_docs:
        chunks = splitter.split_text(raw.page_content)
        for chunk in chunks:
            docs.append(Document(
                page_content=chunk,
                metadata={**raw.metadata, "kb_id": kb_id},
            ))

    if not docs:
        return 0

    vector_store = _get_vector_store()
    vector_store.add_documents(docs)
    return len(docs)


def delete_vectors(kb_id: str, filename: str | None = None) -> int:
    """删除 Milvus 中的向量。filename 为 None 时删除整个知识库的向量。"""
    import re
    if not re.match(r'^[\w-]+$', str(kb_id)):
        raise ValueError("知识库 ID 格式无效")

    expr = f'kb_id == "{kb_id}"'
    if filename:
        safe_filename = filename.replace('"', '\\"')
        expr += f' and filename == "{safe_filename}"'

    vector_store = _get_vector_store()
    # pymilvus Collection.delete()
    collection = vector_store.col
    result = collection.delete(expr)
    return result.delete_count if hasattr(result, 'delete_count') else 0
```

- [ ] **Step 4: internal.py — 新增向量删除端点**

在 `internal_router` 中新增：

```python
@internal_router.delete("/knowledge/vectors")
async def delete_knowledge_vectors(kb_id: str, filename: str | None = None):
    try:
        from app.agent.ingestion import delete_vectors
        count = delete_vectors(kb_id, filename)
        return {"status": "success", "deleted_count": count, "kb_id": kb_id, "filename": filename}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 5: 提交**

```powershell
git add agent/
git commit -m "功能: Agent 支持多格式文档解析（PDF/DOCX/MD）+ 向量删除 API"
```

---

## Task 9: Agent — RAG Artifact + Async + 注入修复 + 系统提示词

**Files:**
- Modify: `agent/app/agent/tools/rag_tool.py`
- Modify: `agent/app/agent/graph.py`

- [ ] **Step 1: 重写 rag_tool.py — Artifact 引用 + 注入修复**

```python
# agent/app/agent/tools/rag_tool.py
import re
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from app.config import settings


@tool(response_format="content_and_artifact")
def rag_search_handler(query: str, config: RunnableConfig) -> tuple[str, list[dict]]:
    """在知识库中检索与问题相关的文档内容，返回带引用标记的上下文和结构化引用元数据"""
    kb_id = config.get("configurable", {}).get("kb_id")
    if not kb_id:
        return "当前上下文中未找到知识库 ID，检索无法进行。", []

    # 防注入校验
    if not re.match(r'^[\w-]+$', str(kb_id)):
        return "知识库 ID 格式无效。", []

    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,
    )

    # 安全表达式（字符串引号包裹）
    search_kwargs = {"expr": f'kb_id == "{kb_id}"'}
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    docs = retriever.invoke(query)
    if not docs:
        return "该知识库中未找到与提问最相关的内容。", []

    # 构建结构化引用（artifact）
    citations = []
    for i, doc in enumerate(docs):
        citations.append({
            "ref": f"Doc {i + 1}",
            "source": doc.metadata.get("filename", "unknown"),
            "snippet": doc.page_content[:200],
            "page": doc.metadata.get("page"),
        })

    # 构建 LLM 上下文（content）
    context = "\n\n".join([f"[Doc {i + 1}] {doc.page_content}" for i, doc in enumerate(docs)])
    return context, citations
```

- [ ] **Step 2: 重写 graph.py — trim_messages + async + 系统提示词**

```python
# agent/app/agent/graph.py
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, trim_messages
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.agent.tools.markdown_loader import load_skills_from_directory
from app.agent.tools.rag_tool import rag_search_handler

SYSTEM_PROMPT = """你是慢病管理平台的 AI 健康顾问。

## 角色定位
- 基于知识库中的专业医疗文献为用户提供循证健康建议
- 回答必须使用中文

## 工具使用规范
- 当用户提出与疾病管理、药物、检查指标相关的问题时，必须先调用 rag_search_handler 检索知识库
- 当问题是日常寒暄或与医疗无关时，直接回答即可

## 回答格式
- 引用知识库内容时使用 [Doc N] 标记，例如"根据 [Doc 1]，建议..."
- 涉及医疗建议时，始终提醒用户"具体方案请咨询主治医师"
- 使用 Markdown 格式提升可读性
"""


def create_agent_graph():
    # Load default tools
    SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
    md_tools = []
    if SKILLS_DIR.exists():
        md_tools = load_skills_from_directory(str(SKILLS_DIR))

    tools = md_tools + [rag_search_handler]

    llm = ChatOpenAI(
        model=settings.CHAT_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    async def assistant_node(state: MessagesState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        # Token 截断 — 保留最近的消息，总量不超过模型上下文的 80%
        messages = trim_messages(
            messages,
            max_tokens=4000,
            token_counter=llm,
            strategy="last",
            start_on="human",
            include_system=True,
        )

        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("assistant", assistant_node)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)
    builder.add_edge("tools", "assistant")

    return builder.compile()
```

- [ ] **Step 3: 提交**

```powershell
git add agent/app/agent/
git commit -m "功能: RAG Artifact 引用 + trim_messages 上下文管理 + 异步修复 + 注入修复"
```

---

## Task 10: Agent — SSE 事件中提取 artifact

**Files:**
- Modify: `agent/app/routers/internal.py`

- [ ] **Step 1: 更新 internal.py 的 tool_end 事件处理**

在 `event_generator` 中，`on_tool_end` 分支需要提取 `ToolMessage.artifact`：

```python
elif kind == "on_tool_end":
    output = event["data"].get("output")
    tool_data: dict[str, object] = {"tool": event["name"]}
    # 提取 content_and_artifact 的 artifact
    if hasattr(output, 'artifact') and output.artifact:
        tool_data["artifact"] = output.artifact
    if hasattr(output, 'content'):
        tool_data["output"] = output.content
    else:
        tool_data["output"] = output
    yield {"event": "tool_end", "data": json.dumps(tool_data, ensure_ascii=False, default=str)}
```

- [ ] **Step 2: 提交**

```powershell
git add agent/app/routers/internal.py
git commit -m "功能: SSE tool_end 事件提取 artifact 引用数据"
```

---

## Task 11: 集成验证

- [ ] **Step 1: 启动所有服务**

```powershell
# 终端1: 基础设施
docker-compose up -d

# 终端2: 后端微服务（Turborepo 全量启动）
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm dev

# 终端3: Agent
cd d:\codes\chronic-disease-management\agent
uv run uvicorn app.main:app --reload --port 8000
```

Expected: 
- Auth service listening on TCP port 8011
- Patient service listening on TCP port 8021
- AI service listening on TCP port 8031
- Agent 启动在 8000

- [ ] **Step 2: 验证 ai-service 会话 CRUD**

使用前端或 curl 测试：
1. 创建会话 → 返回 id
2. 发送聊天 → 流式回复 + 消息被持久化
3. 查询会话列表 → 包含刚创建的会话
4. 重启 Gateway → 会话数据不丢失

- [ ] **Step 3: 最终提交**

```powershell
git add -A
git commit -m "集成: AI 问答模块闭环验证通过"
```
