# Multi-Tenant AI SaaS Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend for a multi-tenant AI SaaS platform featuring document chunking, RAG (Retrieval-Augmented Generation), streaming chat with citations, token tracking, and API Key management.

**Architecture:** A monolithic but logically separated FastAPI application using PostgreSQL (with pgvector and RLS for tenant isolation), Redis (for API rate limiting and quota async tracking), and MinIO (for raw document storage).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), pgvector-python, Redis (redis-py), Boto3 (MinIO), LangChain (for chunking/embedding orchestration).

---

## Chunk 1: Project Setup & Database Models

### Task 1: Initialize Project & Core Infrastructure

**Files:**
- Create: `pyproject.toml`
- Create: `app/main.py`
- Create: `app/core/config.py`
- Create: `app/db/session.py`

- [ ] **Step 1: Setup Poetry and Dependencies**
Run: `poetry init -n`
Run: `poetry add fastapi uvicorn sqlalchemy asyncpg pgvector pydantic-settings redis boto3 pyjwt passlib bcrypt langchain-core langchain-openai tiktoken`
Run: `poetry add --group dev pytest pytest-asyncio httpx`

- [ ] **Step 2: Create Core Config**
Write `app/core/config.py` with `pydantic_settings`. Include `DATABASE_URL`, `REDIS_URL`, `MINIO_URL`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `JWT_SECRET`.

- [ ] **Step 3: Setup Database Session**
Write `app/db/session.py` using `sqlalchemy.ext.asyncio.create_async_engine` and `async_sessionmaker`.

- [ ] **Step 4: Create basic FastAPI app**
Write `app/main.py` configuring the FastAPI app and a `/health` endpoint.

- [ ] **Step 5: Test health endpoint**
Run: `pytest tests/test_main.py` (Create a simple test using `httpx.AsyncClient`)
Expected: PASS

- [ ] **Step 6: Commit**
Run: `git add . && git commit -m "chore: init project and core config"`

### Task 2: Implement Database Models (Users, Orgs, API Keys)

**Files:**
- Create: `app/db/models/base.py`
- Create: `app/db/models/user.py`
- Create: `app/db/models/organization.py`
- Create: `app/db/models/api_key.py`
- Create: `alembic.ini` (run `alembic init alembic`)

- [ ] **Step 1: Create Base Model**
Write `app/db/models/base.py` with SQLAlchemy `DeclarativeBase` and a mixin for `id` (UUID) and `created_at`.

- [ ] **Step 2: Create User & Organization Models**
Write `app/db/models/user.py` (`User` table).
Write `app/db/models/organization.py` (`Organization`, `OrganizationUser` for M:M relation with role ENUM, `OrganizationInvitation`). Includes `quota_tokens_limit` and `quota_tokens_used`.

- [ ] **Step 3: Create API Key Model**
Write `app/db/models/api_key.py` (`ApiKey` table) tracking `key_hash`, `key_prefix`, `qps_limit`, `token_quota`, `token_used`.

- [ ] **Step 4: Generate Alembic Migration**
Run: `alembic revision --autogenerate -m "init auth models"`
Run: `alembic upgrade head`

- [ ] **Step 5: Commit**
Run: `git add . && git commit -m "feat: user, org, and api key models"`

### Task 3: Implement Database Models (Knowledge Base, RAG, Chat)

**Files:**
- Create: `app/db/models/knowledge.py`
- Create: `app/db/models/chat.py`
- Modify: `app/db/models/__init__.py`

- [ ] **Step 1: Create Knowledge Models**
Write `app/db/models/knowledge.py`.
Define `KnowledgeBase` (id, org_id, name).
Define `Document` (id, kb_id, org_id, file_name, minio_url, status).
Define `Chunk` using `pgvector` (id, kb_id, org_id, document_id, content, embedding `Vector(1536)`).

- [ ] **Step 2: Create Chat & Usage Models**
Write `app/db/models/chat.py`.
Define `Conversation` (id, kb_id, org_id, user_id).
Define `Message` (id, conversation_id, role, content, metadata JSONB).
Define `UsageLog` (id, org_id, user_id, api_key_id, model, prompt_tokens, completion_tokens, cost, action_type).

- [ ] **Step 3: Generate Alembic Migration**
Ensure `pgvector` extension is created in the migration script explicitly (`op.execute('CREATE EXTENSION IF NOT EXISTS vector')`).
Run: `alembic revision --autogenerate -m "init rag and chat models"`
Run: `alembic upgrade head`

- [ ] **Step 4: Commit**
Run: `git add . && git commit -m "feat: rag, chat, and usage models"`

---

## Chunk 2: Auth, Isolation, and MinIO

### Task 4: JWT Authentication & RLS Middleware

**Files:**
- Create: `app/core/security.py`
- Create: `app/api/deps.py`

- [ ] **Step 1: JWT Utility Functions**
Write `app/core/security.py`: `create_access_token`, `verify_password`, `get_password_hash`.

- [ ] **Step 2: FastAPI Dependency for User Auth**
Write `app/api/deps.py`: `get_current_user` checking `Authorization: Bearer <token>`.

- [ ] **Step 3: FastAPI Dependency for Organization context & RLS**
In `app/api/deps.py`, write `get_current_org`. Extract `X-Organization-Id` header, verify user belongs to Org.
Inject into db session: `await session.execute(text("SET LOCAL app.current_org_id = :org_id"), {"org_id": org_id})`.

- [ ] **Step 4: Write Tests for Auth & RLS Injection**
Create `tests/api/test_auth_deps.py` to mock JWT and check if RLS variable is set on session.

- [ ] **Step 5: Commit**
Run: `git add . && git commit -m "feat: jwt auth and org context isolation"`

### Task 5: MinIO Integration for Document Upload

**Files:**
- Create: `app/services/storage.py`
- Create: `app/api/endpoints/documents.py`

- [ ] **Step 1: MinIO Client Service**
Write `app/services/storage.py`. Wrap `boto3.client('s3')`. Implement `upload_file(file_bytes, filename, org_id) -> minio_url`.

- [ ] **Step 2: Document Upload Endpoint**
Write `app/api/endpoints/documents.py`.
`POST /api/v1/kb/{kb_id}/documents`.
Requires `get_current_user` and `get_current_org` with at least 'member' role.
Uploads to MinIO -> Creates `Document` row with status `pending`.

- [ ] **Step 3: Test MinIO Service (Mocked)**
Create `tests/services/test_storage.py` mocking Boto3 to return a dummy URL.

- [ ] **Step 4: Commit**
Run: `git add . && git commit -m "feat: document upload to minio"`

---

## Chunk 3: RAG Pipeline & Quota System

### Task 6: Document Parsing & Embedding Pipeline

**Files:**
- Create: `app/services/rag.py`

- [ ] **Step 1: Implement Document Chunking**
Write `app/services/rag.py`. Implement `process_document(document_id)`.
Fetch file from MinIO, parse text. Use `RecursiveCharacterTextSplitter` from LangChain.

- [ ] **Step 2: Generate Embeddings and Save**
In `process_document`, call OpenAI `text-embedding-3-small` (or similar) to generate embeddings for chunks.
Insert rows into `Chunk` table containing `kb_id`, `org_id`, `document_id`, `content`, `embedding`.
Update `Document` status to `completed`.

- [ ] **Step 3: Track Embedding Usage**
In `process_document`, calculate tokens used for embedding. Insert record into `UsageLog`.

- [ ] **Step 4: Test Processing Pipeline (Mocked LLM)**
Create `tests/services/test_rag.py` mocking the embedding API and checking DB inserts.

- [ ] **Step 5: Commit**
Run: `git add . && git commit -m "feat: document processing and embedding pipeline"`

### Task 7: Rate Limiting & Quota Management (Redis)

**Files:**
- Create: `app/services/quota.py`
- Modify: `app/api/deps.py`

- [ ] **Step 1: Quota Checking Service**
Write `app/services/quota.py`. Implement `check_org_quota(org_id)`. Fetch org, check `quota_tokens_used < quota_tokens_limit`. Raise 402 HTTP exception if exceeded.

- [ ] **Step 2: API Key Rate Limiting Service**
Implement `check_api_key_rate_limit(api_key_id)` using Redis Token Bucket. Raise 429 if exceeded.

- [ ] **Step 3: Dependency Integration**
In `app/api/deps.py`, add `verify_quota` dependency that calls `check_org_quota`.

- [ ] **Step 4: Commit**
Run: `git add . && git commit -m "feat: redis rate limiting and quota verification"`

---

## Chunk 4: Streaming Chat & API Gateway

### Task 8: RAG Retrieval & Prompt Assembly

**Files:**
- Create: `app/services/chat.py`

- [ ] **Step 1: Vector Search**
Write `app/services/chat.py`. Implement `retrieve_chunks(query, kb_id, limit=5)`.
Use `pgvector` cosine similarity (`<=>`) queried via SQLAlchemy: `session.scalars(select(Chunk).where(Chunk.kb_id == kb_id).order_by(Chunk.embedding.cosine_distance(query_embedding)).limit(limit))`.

- [ ] **Step 2: Prompt Assembly**
Implement `build_rag_prompt(query, chunks, history)`. Assemble context blocks with source IDs/names.

- [ ] **Step 3: Commit**
Run: `git add . && git commit -m "feat: vector retrieval and rag prompt builder"`

### Task 9: Streaming Chat Endpoint (SSE)

**Files:**
- Create: `app/api/endpoints/chat.py`

- [ ] **Step 1: Setup Streaming Response**
Write `app/api/endpoints/chat.py`.
`POST /api/v1/chat`. Accepts `kb_id`, `conversation_id`, `query`.
Uses `StreamingResponse` from FastAPI.

- [ ] **Step 2: Stream Flow logic**
In the generator:
1. Yield `meta` event with citation list (document names/pages from retrieved chunks).
2. Call LLM (e.g. `ChatOpenAI.astream`). Yield `chunk` events containing text deltas.
3. On completion, calculate tokens (using `tiktoken` or LLM usage metadata).
4. Save User `Message` and Assistant `Message` (with `metadata` containing citations and tokens) to DB.
5. Save to `UsageLog`.
6. Yield `done` event.

- [ ] **Step 3: Test Streaming Endpoint**
Create `tests/api/test_chat.py`. Mock the LLM stream and test the SSE response format.

- [ ] **Step 4: Commit**
Run: `git add . && git commit -m "feat: sse streaming chat endpoint with citations"`

### Task 10: API Key Gateway for External Access

**Files:**
- Create: `app/api/endpoints/external_api.py`
- Modify: `app/api/deps.py`

- [ ] **Step 1: API Key Auth Dependency**
In `app/api/deps.py`, write `get_api_key_context`.
Extract `Authorization: Bearer sk_...`. Hash it, lookup `api_keys` table.
Apply Redis Rate Limit (`check_api_key_rate_limit`).
Check API Key specific quota and Org quota.
Set `app.current_org_id` for RLS.

- [ ] **Step 2: External Chat Endpoint**
Write `app/api/endpoints/external_api.py`.
`POST /v1/chat/completions` (OpenAI compatible shape).
Uses `get_api_key_context`. Proxies to RAG logic, logs usage against `api_key_id`.

- [ ] **Step 3: Test External API**
Create `tests/api/test_external_api.py`. Test key hashing, rate limit rejections, and success flow.

- [ ] **Step 4: Commit**
Run: `git add . && git commit -m "feat: external api gateway with key auth and rate limits"`
