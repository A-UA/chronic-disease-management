# ARQ Redis Document Task Integration Plan

**Goal:** Add real Redis-backed integration tests for document ingestion and file cleanup tasks without changing runtime semantics.

**Architecture:** Tests enqueue through the existing service helpers, resolve tasks from `WorkerSettings.functions`, and execute real task functions against real Redis with controlled collaborators.

**Tech Stack:** pytest, arq, Redis, SQLAlchemy async

---

### Task 1: Add Redis-backed ingestion integration tests

**Files:**
- Create: `backend/tests/integration/test_arq_document_tasks.py`
- Modify: test fixtures as needed under `backend/tests`

- [ ] **Step 1: Write the failing test**

Add integration tests for:
- ingestion success state transition
- ingestion failure writeback

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_arq_document_tasks.py -v`

- [ ] **Step 3: Write minimal implementation**

Add Redis fixtures and task execution helpers needed to enqueue and execute the registered worker functions.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_arq_document_tasks.py -v`

### Task 2: Cover file cleanup task integration

**Files:**
- Modify: `backend/tests/integration/test_arq_document_tasks.py`
- Modify: `backend/app/services/rag/tasks.py` or `backend/app/tasks/worker.py` only if required for testability

- [ ] **Step 1: Write the failing test**

Add a cleanup task integration test that verifies:
- `enqueue_delete_file_job` pushes a real job
- the registered worker function executes
- storage delete entrypoint is called

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_arq_document_tasks.py -k "delete" -v`

- [ ] **Step 3: Write minimal implementation**

Register or expose only what is necessary for the cleanup task to be consumed and asserted in tests.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_arq_document_tasks.py -k "delete" -v`

### Task 3: Run verification

**Files:**
- Modify: any fallout files required by verification

- [ ] **Step 1: Run focused suite**

Run:
- `uv run pytest tests/integration/test_arq_document_tasks.py -v`

- [ ] **Step 2: Run broader regression**

Run:
- `uv run pytest tests -v`

- [ ] **Step 3: Run queue-path code search**

Run:
- `rg -n "enqueue_process_document_job|enqueue_delete_file_job|process_document_task|delete_file_task" backend/app backend/tests -S`
