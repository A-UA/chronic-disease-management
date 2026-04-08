# Chat Agent Route Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add route-level integration tests for `/api/v1/chat` covering standard chat and agent chat SSE flows with real database persistence.

**Architecture:** Tests use the real FastAPI app and real database, but override auth/quota/db dependencies and stub unstable AI integrations. Coverage stays centered on route dispatch, SSE protocol shape, and persisted conversation/message side effects.

**Tech Stack:** FastAPI, httpx, pytest, pytest-asyncio, SQLAlchemy async, PostgreSQL

---

### Task 1: Add standard chat route integration coverage

**Files:**
- Create: `backend/tests/integration/test_chat_route_integration.py`

- [ ] **Step 1: Write the failing test**

Add a route integration test that posts to `/api/v1/chat` with `use_agent=false` and asserts:
- HTTP 200
- `text/event-stream`
- `meta`, `chunk`, `done` events
- persisted `Conversation` and `Message` rows

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_chat_route_integration.py -k "standard" -v`

- [ ] **Step 3: Write minimal implementation**

Add local fixtures for:
- dependency overrides
- test tenant/user/org/kb records
- SSE parsing
- standard chat stubs for retrieval, prompt, citations, and LLM streaming

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_chat_route_integration.py -k "standard" -v`

### Task 2: Add agent chat route integration coverage

**Files:**
- Modify: `backend/tests/integration/test_chat_route_integration.py`

- [ ] **Step 1: Write the failing test**

Add a route integration test that posts to `/api/v1/chat` with `use_agent=true` and asserts:
- HTTP 200
- `text/event-stream`
- `meta`, `chunk`, `done` events
- persisted assistant message contains `agent_mode`

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_chat_route_integration.py -k "agent" -v`

- [ ] **Step 3: Write minimal implementation**

Add agent stubs for:
- `run_agent`
- optional permission resolution if needed by the route path

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_chat_route_integration.py -k "agent" -v`

### Task 3: Add failure visibility coverage and verify regression

**Files:**
- Modify: `backend/tests/integration/test_chat_route_integration.py`

- [ ] **Step 1: Write the failing test**

Add one failure-path integration test that verifies a stubbed downstream failure is visible to the caller instead of looking like a normal completed stream.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_chat_route_integration.py -k "failure" -v`

- [ ] **Step 3: Write minimal implementation**

Adjust route test fixtures or assertions only as needed to capture the failure mode without changing production behavior.

- [ ] **Step 4: Run focused suite**

Run: `uv run pytest tests/integration/test_chat_route_integration.py -v`

- [ ] **Step 5: Run broader regression**

Run: `uv run pytest tests -v`

- [ ] **Step 6: Run route-path code search**

Run: `rg -n "/api/v1/chat|handle_standard_chat|handle_agent_chat|StreamingResponse|text/event-stream" backend/app backend/tests -S`
