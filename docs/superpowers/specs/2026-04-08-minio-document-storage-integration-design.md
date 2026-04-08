# MinIO Document Storage Integration Design

**Date:** 2026-04-08

**Scope:** `backend/tests`, with real MinIO access through the existing storage service and document task flow

## Goal

Add real MinIO-backed integration tests for document storage. The tests must verify that uploads create real objects and cleanup tasks remove those objects.

## Constraints

- Use the MinIO instance from `docker compose`
- Do not change request or task semantics
- Allow test-specific object key isolation only
- Prefer existing service and task entrypoints over direct low-level calls when possible

## Chosen Approach

Use the real `StorageService` and real MinIO bucket, but isolate each test with a unique object prefix.

Coverage will include both:

- direct storage service behavior
- the existing document upload and cleanup task path

This gives stronger signal than a pure storage unit test because it confirms the application produces usable `minio_url` values and that cleanup paths delete the actual object.

## Test Coverage

### 1. Direct storage upload/delete

Flow:

`StorageService.upload_file -> MinIO object exists -> StorageService.delete_file -> MinIO object absent`

Assertions:

- returned `minio_url` is parseable
- object exists after upload
- object no longer exists after delete

### 2. Document upload service creates a real object

Flow:

`document_service.upload_document_and_enqueue -> minio_url -> MinIO object exists`

Assertions:

- returned `minio_url` points to a real object
- service output and object state are aligned

### 3. Cleanup task removes a real object

Flow:

`enqueue_delete_file_job -> Redis -> delete_file_task -> MinIO object removed`

Assertions:

- cleanup job executes
- uploaded object is actually deleted from MinIO

## Isolation Strategy

- Each test uses a unique organization id or unique filename-derived prefix
- Each test tracks the object key it creates
- Finalizers delete any leftover object if cleanup did not complete

This avoids test interference inside the shared bucket.

## Required Fixtures

- real MinIO client fixture using current backend settings
- helper to convert `minio_url` to bucket/key
- object cleanup fixture for best-effort teardown
- optional reuse of the Redis queue fixture from the previous integration slice

## Risks

### 1. Shared bucket pollution

If a test crashes after upload, objects can accumulate.

Mitigation:

- always register cleanup by key
- best-effort delete in teardown

### 2. Eventual consistency assumptions

Although MinIO is typically immediate, tests should not assume timing more than necessary.

Mitigation:

- use `head_object` or direct existence checks after awaited operations

### 3. Overlapping test scope with Redis integration

Storage and queue integration can become coupled and harder to debug.

Mitigation:

- keep one direct storage test
- keep one service-level upload test
- keep one cleanup-task test

## Acceptance Criteria

- tests talk to the real MinIO from `docker compose`
- uploaded objects are confirmed to exist
- cleanup paths are confirmed to delete those objects
- tests leave no intentional storage residue
