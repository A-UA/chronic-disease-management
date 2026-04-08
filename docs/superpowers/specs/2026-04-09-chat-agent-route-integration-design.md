# Chat Agent Route Integration Design

**Date:** 2026-04-09

**Scope:** `backend/tests`, with real FastAPI routing and real database persistence for `/api/v1/chat`

## Goal

Add route-level integration coverage for the converged chat runtime. The tests must verify that the real `/api/v1/chat` entrypoint correctly dispatches standard chat and agent chat, emits valid SSE responses, and persists conversation/message records.

## Constraints

- Use the real FastAPI app and the real `/api/v1/chat` route
- Use the real database
- Override route dependencies for auth, tenant, org, quota, and db session
- Do not change business semantics
- Keep LLM, retrieval, and agent execution deterministic with stubs

## Chosen Approach

Use real route integration tests with `dependency_overrides` on the application. The tests will exercise the HTTP layer, route dispatch, and persistence side effects while replacing unstable AI dependencies with controlled stubs.

This gives stronger coverage than service-only tests because it confirms the runtime entrypoint, dependency injection, and SSE response shape after the recent backend convergence.

## Test Coverage

### 1. Standard chat route integration

Flow:

`POST /api/v1/chat -> chat_runtime -> handle_standard_chat -> SSE -> DB persistence`

Assertions:

- response status is `200`
- response `content-type` is `text/event-stream`
- SSE contains `meta`, `chunk`, and `done`
- SSE `conversation_id` maps to a real `Conversation`
- database contains one `user` message and one `assistant` message for that conversation

### 2. Agent chat route integration

Flow:

`POST /api/v1/chat(use_agent=true) -> chat_runtime -> handle_agent_chat -> SSE -> DB persistence`

Assertions:

- response status is `200`
- response `content-type` is `text/event-stream`
- SSE contains `meta`, `chunk`, and `done`
- persisted assistant message includes `agent_mode`
- persisted messages belong to the same conversation referenced by SSE

### 3. Failure visibility

Flow:

`POST /api/v1/chat -> stubbed downstream failure`

Assertions:

- request does not silently succeed with a normal completed stream
- failure is observable as a non-200 response or an interrupted/error stream

## Isolation Strategy

- Create test-scoped `Tenant`, `User`, `Organization`, and `KnowledgeBase`
- Override route dependencies instead of going through real JWT auth and quota checks
- Stub retrieval, prompt building, citation extraction, LLM streaming, and agent execution
- Clean up created `Conversation` and `Message` rows after each test

## Required Fixtures

- real app fixture with temporary `dependency_overrides`
- real async db session fixture
- test data fixture for tenant/user/org/kb
- helper to parse SSE event text into ordered event records

## Risks

### 1. Route tests overlapping existing service tests

Mitigation:

- keep assertions focused on routing, SSE, and persistence
- do not re-test internal retrieval logic already covered elsewhere

### 2. Streaming assertions becoming brittle

Mitigation:

- assert event structure and key payloads, not exact full stream formatting

### 3. Dependency override leakage across tests

Mitigation:

- clear `app.dependency_overrides` in fixture teardown

## Acceptance Criteria

- real `/api/v1/chat` route is exercised for both standard and agent modes
- SSE event structure is parseable and valid
- persisted conversation and message records match the SSE response
- broader backend test suite remains green
