# MinIO Document Storage Integration Plan

**Goal:** Add real MinIO-backed integration tests for document upload and cleanup behavior.

**Architecture:** Tests use the real storage service, real MinIO bucket, and the existing document upload and cleanup task paths with isolated object keys.

**Tech Stack:** pytest, aioboto3, MinIO, arq, Redis

---

### Task 1: Add direct storage integration coverage

**Files:**
- Create: `backend/tests/integration/test_minio_document_storage.py`

- [x] **Step 1: Write the failing test**

Add a direct storage integration test that:
- uploads bytes through `StorageService`
- confirms object existence
- deletes the object
- confirms object absence

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_minio_document_storage.py -k "storage" -v`

- [x] **Step 3: Write minimal implementation**

Add MinIO fixtures and helpers needed to inspect object existence and perform cleanup.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_minio_document_storage.py -k "storage" -v`

### Task 2: Add service/task-backed storage integration coverage

**Files:**
- Modify: `backend/tests/integration/test_minio_document_storage.py`

- [x] **Step 1: Write the failing test**

Add tests that verify:
- `upload_document_and_enqueue` produces a `minio_url` for a real stored object
- `delete_file_task` removes a real uploaded object

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_minio_document_storage.py -k "document or cleanup" -v`

- [x] **Step 3: Write minimal implementation**

Reuse existing Redis/task fixtures where practical, adding only the storage assertions and cleanup helpers.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_minio_document_storage.py -v`

### Task 3: Run verification

**Files:**
- Modify: any fallout files required by verification

- [x] **Step 1: Run focused suite**

Run:
- `uv run pytest tests/integration/test_minio_document_storage.py -v`

- [x] **Step 2: Run broader regression**

Run:
- `uv run pytest tests -v`

- [x] **Step 3: Run storage-path code search**

Run:
- `rg -n "upload_file|delete_file|minio_url|delete_file_task" backend/app backend/tests -S`

## Verification Result

- `uv run pytest tests/integration/test_minio_document_storage.py -v`
- `uv run pytest tests -v`
- `rg -n "upload_file|delete_file|minio_url|delete_file_task" backend/app backend/tests -S`

Current outcome:
- `27 passed, 1 warning`
