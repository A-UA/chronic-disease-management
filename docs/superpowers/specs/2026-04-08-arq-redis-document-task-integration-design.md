# ARQ Redis Document Task Integration Design

**Date:** 2026-04-08

**Scope:** `backend/tests`, with limited testability adjustments in `backend/app/services/rag/tasks.py` and `backend/app/tasks/worker.py`

## Goal

Add a real Redis-backed integration test slice for document async tasks. The tests must verify enqueue, consume, and database state transitions for document ingestion and storage cleanup without changing business semantics.

## Constraints

- Use the real Redis instance from `docker compose`
- Do not introduce a separate worker process for tests
- Keep application runtime behavior unchanged
- Allow only minimal testability seams when necessary

## Chosen Approach

Use the real enqueue path (`enqueue_*`) and real `arq` task functions, but let tests own consumption.

This gives:

- real Redis connectivity
- real job payloads
- real task function execution
- deterministic control over success and failure cases

It deliberately does not validate a separate worker process lifecycle. That is deferred in favor of stable, deterministic integration coverage.

## Test Coverage

### 1. Document ingestion success

Flow:

`enqueue_process_document_job -> Redis -> process_document_task -> DB update`

Assertions:

- job is enqueued
- task can be consumed and executed
- `Document.status` becomes `completed`

### 2. Document ingestion failure

Flow:

`enqueue_process_document_job -> Redis -> process_document_task -> exception -> DB failure writeback`

Assertions:

- task is consumed
- exception path is hit
- `Document.status` becomes `failed`
- `failed_reason` is written

### 3. File cleanup task success

Flow:

`enqueue_delete_file_job -> Redis -> delete_file_task`

Assertions:

- cleanup job is enqueued
- task is consumed
- storage delete entrypoint is invoked

## Execution Model in Tests

Tests will:

1. enqueue jobs through the existing service helpers
2. inspect Redis-backed queued work
3. execute the mapped worker function directly using the same function registry that production uses

This keeps the system boundary aligned with the current architecture:

- enqueue path is real
- worker function resolution is real
- side-effect collaborators can still be patched for deterministic assertions

## Required Test Fixtures

- Redis fixture that connects to the configured test Redis and clears queued jobs before and after each test
- Database fixture for creating and reloading `Document` rows
- Helper to resolve a queued job to the corresponding function in `WorkerSettings.functions`

## Minimal Code Changes Allowed

- export or expose enough task metadata for tests to resolve and execute queued jobs cleanly
- register the file cleanup task in `WorkerSettings`
- no API contract changes
- no queue contract changes

## Risks

### 1. Redis queue cleanup leakage

If tests leave jobs behind, later tests become flaky.

Mitigation:

- isolate queue cleanup in fixtures
- assert queue empties after execution

### 2. Over-mocking defeats the integration goal

If ingestion or cleanup paths are mocked too deeply, the tests collapse back into unit tests.

Mitigation:

- only patch heavyweight collaborators or failure injection points
- keep enqueue and task resolution real

### 3. Worker internals drift from tests

If task registration changes, tests can silently stop reflecting runtime.

Mitigation:

- resolve task execution through `WorkerSettings.functions`
- avoid hardcoding alternate task maps in tests

## Acceptance Criteria

- tests use the real Redis configured for the backend
- enqueue helpers are exercised directly
- worker task functions execute through the registered runtime mapping
- ingestion success and failure state transitions are verified
- file cleanup task execution is verified
