# Backend App/AI/Plugins Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace duplicated backend runtime paths with one canonical path for permissions, RAG chat, document ingestion, and agent orchestration while preserving external API behavior.

**Architecture:** Move orchestration out of routers and into service modules, keep AI modules focused on pure computation, and make plugin/provider access explicit through one provider service. Delete legacy RAG and compatibility modules once all imports are migrated.

**Tech Stack:** FastAPI, SQLAlchemy async, pytest, arq, PostgreSQL RLS, Redis, plugin registry

---

### Task 1: Close the RBAC Permission Graph

**Files:**
- Modify: `backend/app/routers/system/api_keys.py`
- Modify: `backend/app/seed.py`
- Test: `backend/tests/...` permission-related test module to be created near existing router/auth tests

- [ ] **Step 1: Write the failing test**

Write a test that enumerates route permission codes used by the changed system routes and asserts each code exists in seeded permissions. Include `api_keys` route coverage.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "permission and api_key" -v`
Expected: FAIL because `org:manage` is referenced but not seeded.

- [ ] **Step 3: Write minimal implementation**

Replace `org:manage` usage with the seeded management permission that matches current product semantics, or extend the seed/runtime catalog consistently if a new code is truly required. Prefer convergence on existing seeded codes.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "permission and api_key" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/system/api_keys.py backend/app/seed.py backend/tests
git commit -m "refactor: align route permissions with seeded rbac codes"
```

### Task 2: Introduce an Explicit Provider Service

**Files:**
- Create: `backend/app/services/rag/provider_service.py`
- Modify: `backend/app/services/rag/__init__.py`
- Test: `backend/tests/...` provider service test module

- [ ] **Step 1: Write the failing test**

Write tests that verify the provider service returns llm, embedding, reranker, chunker, and parser providers through one API and normalizes missing-provider failures.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "provider_service" -v`
Expected: FAIL because the service module does not exist.

- [ ] **Step 3: Write minimal implementation**

Add `provider_service.py` with explicit getters wrapping `PluginRegistry.get(...)` and stable exception translation for caller-facing use.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "provider_service" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rag/provider_service.py backend/app/services/rag/__init__.py backend/tests
git commit -m "refactor: add explicit rag provider service"
```

### Task 3: Extract Prompt and Conversation Helpers from Old Chat Module

**Files:**
- Create: `backend/app/ai/rag/prompt.py`
- Create: `backend/app/ai/rag/conversation.py`
- Modify: `backend/app/ai/rag/retrieval.py`
- Modify: `backend/app/routers/rag/chat.py` or interim call sites as needed
- Test: `backend/tests/...` rag helper tests

- [ ] **Step 1: Write the failing test**

Write focused tests for prompt construction and history transformation helpers, based on existing runtime behavior.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "rag_prompt or conversation_history" -v`
Expected: FAIL because the helper modules do not exist.

- [ ] **Step 3: Write minimal implementation**

Move prompt building and history/query helper logic out of `ai/rag/chat_service.py` into the new helper modules without changing output shape.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "rag_prompt or conversation_history" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/rag/prompt.py backend/app/ai/rag/conversation.py backend/app/ai/rag/retrieval.py backend/tests
git commit -m "refactor: extract rag prompt and conversation helpers"
```

### Task 4: Move Chat Orchestration into a Service Layer

**Files:**
- Create: `backend/app/services/rag/chat_service.py`
- Modify: `backend/app/routers/rag/chat.py`
- Modify: `backend/app/services/rag/__init__.py`
- Test: `backend/tests/...` chat service tests

- [ ] **Step 1: Write the failing test**

Write service-layer tests for:
- creating/loading conversations
- retrieving chunks through AI helpers
- persisting user/assistant messages
- updating usage/quota
- preserving SSE event contract

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "rag_chat_service" -v`
Expected: FAIL because the orchestration service does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement `services/rag/chat_service.py` and make the router delegate to it. Remove business orchestration from the router.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "rag_chat_service or chat_endpoint" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rag/chat_service.py backend/app/routers/rag/chat.py backend/app/services/rag/__init__.py backend/tests
git commit -m "refactor: move rag chat orchestration into service layer"
```

### Task 5: Move Document Upload and Enqueue Orchestration into a Service Layer

**Files:**
- Create: `backend/app/services/rag/document_service.py`
- Modify: `backend/app/routers/rag/documents.py`
- Modify: `backend/app/services/rag/tasks.py`
- Test: `backend/tests/...` document service tests

- [ ] **Step 1: Write the failing test**

Write tests for:
- parser selection through plugin-backed provider service
- storage upload
- document creation
- queue enqueue success/failure behavior

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "document_service" -v`
Expected: FAIL because the service does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement `services/rag/document_service.py`, make the router delegate to it, and make `arq` the canonical async path instead of request-local `BackgroundTasks`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "document_service or upload_document" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rag/document_service.py backend/app/routers/rag/documents.py backend/app/services/rag/tasks.py backend/tests
git commit -m "refactor: move document ingestion orchestration into service layer"
```

### Task 6: Purify the AI Ingestion Pipeline

**Files:**
- Modify: `backend/app/ai/rag/ingestion.py`
- Modify: `backend/app/services/rag/tasks.py`
- Test: `backend/tests/...` ingestion pipeline tests

- [ ] **Step 1: Write the failing test**

Write tests asserting `ai/rag/ingestion.py` accepts injected dependencies/context instead of creating sessions or performing quota side effects itself.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "ingestion_pipeline" -v`
Expected: FAIL because the current module creates its own session and quota side effects.

- [ ] **Step 3: Write minimal implementation**

Refactor ingestion to operate on an injected session/provider set and leave status/quota orchestration to task/service callers.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "ingestion_pipeline" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/rag/ingestion.py backend/app/services/rag/tasks.py backend/tests
git commit -m "refactor: remove service-side effects from ai ingestion pipeline"
```

### Task 7: Align Agent Runtime with Its Real Execution Model

**Files:**
- Create: `backend/app/services/agent/service.py`
- Modify: `backend/app/routers/rag/chat.py`
- Modify: `backend/app/ai/agent/__init__.py`
- Modify: `backend/app/ai/agent/graph.py`
- Test: `backend/tests/...` agent service tests

- [ ] **Step 1: Write the failing test**

Write tests for agent-mode orchestration that verify:
- permission resolution
- security context construction
- message persistence
- agent result handling

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "agent_service" -v`
Expected: FAIL because orchestration is still embedded in the router and runtime model is inconsistent.

- [ ] **Step 3: Write minimal implementation**

Move agent-mode orchestration into `services/agent/service.py` and simplify AI runtime so the code reflects the actual execution model instead of an unused graph abstraction.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "agent_service or use_agent" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/service.py backend/app/routers/rag/chat.py backend/app/ai/agent/__init__.py backend/app/ai/agent/graph.py backend/tests
git commit -m "refactor: align agent orchestration with service runtime"
```

### Task 8: Migrate Call Sites off Compatibility and Legacy Modules

**Files:**
- Modify: all remaining import sites under `backend/app`
- Test: `backend/tests/...` import/path regression tests

- [ ] **Step 1: Write the failing test**

Write a codebase-level test or static assertion that fails if production modules import:
- `app.plugins.provider_compat`
- `app.ai.rag.ingestion_legacy`
- `app.ai.rag.llm_legacy`
- `app.ai.rag.reranker_legacy`
- `app.ai.rag.chat_service`

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "legacy_imports" -v`
Expected: FAIL while old imports still exist.

- [ ] **Step 3: Write minimal implementation**

Migrate all production call sites to the new services/ai modules and remove the compatibility imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "legacy_imports" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "refactor: migrate production code off legacy rag modules"
```

### Task 9: Delete Dead Modules

**Files:**
- Delete: `backend/app/ai/rag/chat_service.py`
- Delete: `backend/app/ai/rag/document_parser.py`
- Delete: `backend/app/ai/rag/ingestion_legacy.py`
- Delete: `backend/app/ai/rag/llm_legacy.py`
- Delete: `backend/app/ai/rag/reranker_legacy.py`
- Delete: `backend/app/plugins/provider_compat.py`
- Test: existing tests plus import/path regression tests

- [ ] **Step 1: Write the failing test**

If not already covered, extend the import regression test so dead modules must not be referenced anywhere in production code.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests -k "legacy_imports" -v`
Expected: FAIL until all references are removed.

- [ ] **Step 3: Write minimal implementation**

Delete the dead modules and clean any remaining import or `__init__` fallout.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests -k "legacy_imports" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "refactor: delete dead rag compatibility modules"
```

### Task 10: Run Verification for the Converged Backend

**Files:**
- Modify: any fallout files required by verification
- Test: targeted and broader backend suites

- [ ] **Step 1: Run focused regression suites**

Run:
- `uv run pytest backend/tests -k "permission or provider_service or rag_chat_service or document_service or ingestion_pipeline or agent_service or legacy_imports" -v`

Expected: PASS

- [ ] **Step 2: Run broader backend verification**

Run:
- `uv run pytest backend/tests -v`

Expected: PASS, or report exact remaining failures and stop for cleanup.

- [ ] **Step 3: Run code search verification**

Run:
- `rg -n "provider_compat|ingestion_legacy|llm_legacy|reranker_legacy|from app\\.ai\\.rag\\.chat_service" backend/app`

Expected: no matches in production code.

- [ ] **Step 4: Commit final convergence result**

```bash
git add backend/app backend/tests docs/superpowers/specs/2026-04-08-backend-app-ai-plugins-convergence-design.md docs/superpowers/plans/2026-04-08-backend-app-ai-plugins-convergence.md
git commit -m "refactor: converge backend app ai and plugin runtime paths"
```
