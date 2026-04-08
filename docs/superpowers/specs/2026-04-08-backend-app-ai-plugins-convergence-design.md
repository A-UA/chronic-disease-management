# Backend App/AI/Plugins Convergence Design

**Date:** 2026-04-08

**Scope:** `backend/app`, with focus on `backend/app/ai` and `backend/app/plugins`

## Goal

Perform a one-time structural convergence of the backend runtime paths without changing external API semantics or frontend contracts. The result should make permissions, RAG, document ingestion, and agent execution follow one primary implementation path each.

## Current Problems

### 1. Duplicate runtime paths

- RAG logic is split across `ai/rag/chat_service.py`, `ai/rag/retrieval.py`, and `ai/rag/citation.py`.
- Document parsing exists both in `ai/rag/document_parser.py` and `plugins/parser/*`.
- Legacy compatibility modules remain active in real request paths.

This creates multiple sources of truth for the same behavior.

### 2. Layer boundaries are declared but not enforced

- Routers perform business orchestration instead of acting as thin HTTP adapters.
- AI modules create their own database sessions and depend on service-layer quota/redis helpers.
- Plugin access is spread across the codebase through implicit side-effect registration and compatibility wrappers.

This means the repo has directory layering, but not runtime layering.

### 3. Permission model is not fully closed

- Runtime permission checks and seeded permission codes diverge.
- At least one route family uses permission codes that are not present in the seeded RBAC catalog.

This breaks the end-to-end authorization contract.

### 4. Async execution is inconsistent

- Some flows use `BackgroundTasks`.
- Some use `asyncio.create_task`.
- Some define `arq` tasks but do not make them the canonical execution path.

This prevents a single operational model for retries, status transitions, and failure handling.

### 5. Agent architecture is overstated

- `ai/agent/graph.py` defines a LangGraph-style graph.
- `ai/agent/__init__.py` does not execute that graph as the real runtime.

The code advertises one execution model and runs another.

## Design Principles

### 1. One runtime path per capability

Each of the following must have exactly one canonical execution path:

- chat
- document upload and ingestion
- agent execution
- permission enforcement

Compatibility code may exist briefly during the change, but must not remain as a long-term alternate path.

### 2. Real dependency direction

Runtime dependency direction becomes:

- `routers -> services -> ai -> plugins/models/base`

Additional rules:

- routers may not orchestrate long-running business workflows
- services may open sessions, enqueue jobs, update quota, and persist records
- ai may not create sessions or depend on service-layer redis/quota helpers
- plugins may not contain business orchestration

### 3. Explicit runtime composition

Provider/plugin loading should remain centralized, but business modules must stop depending on compatibility wrappers such as `provider_compat.py`. Services should obtain providers through an explicit provider facade or direct registry access behind one service abstraction.

### 4. External stability, internal replacement

Allowed:

- moving orchestration out of routers
- deleting duplicated internal modules
- replacing `BackgroundTasks` primary paths with queue-backed execution
- replacing pseudo-graph runtime with explicit orchestrator runtime

Not allowed:

- changing request/response shapes for current public endpoints
- changing frontend-visible route semantics
- changing permission meanings without corresponding seed/runtime alignment

## Target Architecture

## Runtime Flows

### Chat flow

`routers/rag/chat.py -> services/rag/chat_service.py -> ai/rag/* -> plugins/* -> services persistence/quota`

Responsibilities:

- router: request validation, auth dependencies, HTTP response type
- service: conversation loading, filter normalization, provider retrieval, SSE orchestration, message persistence, usage/quota updates
- ai: retrieval, citation extraction, prompt construction, history transformation

### Document flow

`routers/rag/documents.py -> services/rag/document_service.py -> plugins/parser/* -> storage -> enqueue arq task -> services/rag/tasks.py -> ai/rag/ingestion.py`

Responsibilities:

- router: file upload protocol and error mapping
- service: parse, upload to storage, create `Document`, enqueue task
- task: set runtime context, call ingestion pipeline, update document status
- ai ingestion: chunking, embedding preparation, chunk persistence payload generation

### Agent flow

`routers/rag/chat.py -> services/agent/service.py -> ai/agent/* -> ai/rag/* -> services persistence`

Responsibilities:

- service builds `SecurityContext`, resolves effective permissions, loads/saves conversation messages
- ai agent decides whether to use direct answer, skill, or rag flow
- ai agent no longer pretends to be running a graph engine if it is not

## Module Decisions

### Keep and strengthen

- `backend/app/plugins/*`
- `backend/app/ai/rag/retrieval.py`
- `backend/app/ai/rag/citation.py`
- `backend/app/ai/rag/ingestion.py`
- `backend/app/ai/agent/*`

### Delete

- `backend/app/ai/rag/chat_service.py`
- `backend/app/ai/rag/document_parser.py`
- `backend/app/ai/rag/ingestion_legacy.py`
- `backend/app/ai/rag/llm_legacy.py`
- `backend/app/ai/rag/reranker_legacy.py`
- `backend/app/plugins/provider_compat.py`

### Add

- `backend/app/services/rag/chat_service.py`
- `backend/app/services/rag/document_service.py`
- `backend/app/services/rag/provider_service.py`
- `backend/app/services/agent/service.py`
- `backend/app/ai/rag/prompt.py`
- `backend/app/ai/rag/conversation.py`

## Detailed Responsibilities

### `services/rag/chat_service.py`

Owns:

- chat request orchestration
- conversation creation/loading
- history loading and normalization
- provider access via provider service
- SSE generation
- assistant message persistence
- usage log creation
- quota updates

Must not own:

- vector search details
- citation extraction internals
- plugin registration

### `services/rag/document_service.py`

Owns:

- parser selection through plugin system
- storage upload
- `Document` row creation
- task enqueue
- enqueue failure handling

Must not own:

- chunk splitting logic
- embedding generation details

### `services/rag/provider_service.py`

Owns:

- explicit access to llm/embedding/reranker/chunker/parser providers
- default provider resolution
- provider creation error normalization

This becomes the single provider access seam used by services.

### `services/agent/service.py`

Owns:

- permission resolution for agent mode
- security context construction
- conversation persistence for agent flow
- calling `ai.agent.run_agent`

### `ai/rag/prompt.py`

Owns:

- build prompt from query and retrieved chunks
- build prompt metadata needed by services

### `ai/rag/conversation.py`

Owns:

- retrieval query enhancement from history
- token-budget history trimming
- compression-related pure helpers that do not require service-layer side effects

## Permission Closure

Permission codes must be unified around a single seeded catalog.

Required outcome:

- every `check_permission("...")` code exists in seed data
- every seeded privileged code has a coherent runtime use
- no route depends on an unseeded permission code

This is a hard gate because the architecture is not coherent if access control is not coherent.

## Failure Handling

### Provider failures

- service layer converts provider construction and runtime failures into stable business errors
- routers do not expose raw provider exceptions

### Chat failures

- SSE generation must still persist an interrupted assistant message if generation started
- usage accounting records actual consumed tokens only

### Document failures

- enqueue failure is surfaced explicitly and must not leave a silently pending document
- ingestion failure updates `Document.status` from one canonical location

### Audit/task failures

- queue-backed task execution becomes the primary async model for long-running work
- fire-and-forget asyncio usage should be removed from primary flows

## Testing Strategy

### Required regression coverage

- permission-code consistency tests
- service-layer chat orchestration tests
- service-layer document upload/enqueue tests
- ingestion task status transition tests
- plugin/provider resolution tests
- agent service orchestration tests

### Test boundary rule

- routers: protocol tests only
- services: orchestration tests
- ai: pure logic and dependency interaction tests
- plugins: registration and adapter tests

## Migration Order

1. Align seeded permissions and route permission checks.
2. Introduce provider service and move business code off compatibility wrapper.
3. Introduce service-layer chat orchestration and thin the chat router.
4. Introduce service-layer document orchestration and move to canonical queue path.
5. Split prompt/conversation helpers out of old chat module.
6. Remove duplicated parser and legacy rag modules.
7. Simplify agent runtime to match actual execution model.
8. Run focused regression tests, then broader backend verification.

## Risks

### 1. Broad regression surface

The change touches auth, RAG, queueing, and persistence boundaries simultaneously.

Mitigation:

- move behavior under tests before deleting old modules
- keep router contracts stable

### 2. Hidden legacy imports

Old modules may still be imported from unexpected places.

Mitigation:

- search all imports before deletion
- replace imports with new service/ai module paths before removing files

### 3. Queue path mismatch in development

Developers may rely on request-local background execution.

Mitigation:

- make enqueue behavior explicit
- fail fast when queue submission fails

## Acceptance Criteria

- no production code imports from `ai/rag/*legacy*`
- no production code imports `app.plugins.provider_compat`
- no production route performs chat or ingestion orchestration directly
- parser logic is sourced only from `plugins/parser/*`
- `ai` modules no longer create their own sessions
- route permission checks match seeded permission codes
- canonical tests cover chat, ingestion, permissions, and agent orchestration
