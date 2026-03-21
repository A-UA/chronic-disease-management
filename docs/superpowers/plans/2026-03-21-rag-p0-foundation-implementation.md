# RAG P0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable RAG foundation slice by fixing test/runtime setup and implementing real document parsing plus structured chunking.

**Architecture:** Keep the current FastAPI and SQLAlchemy structure, but separate document ingestion into focused units: parser, chunker, and embedding provider boundary. Execute the work in small TDD steps so the ingestion path becomes testable before retrieval and generation are upgraded.

**Tech Stack:** Python, FastAPI, SQLAlchemy async, pytest, httpx, pgvector

---

### Task 1: Fix Local Test Import Path

**Files:**
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_main.py`

- [ ] **Step 1: Write the failing test command**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_main.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 2: Add pytest import path config**

Create `backend/pytest.ini`:

```ini
[pytest]
pythonpath = .
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: Add shared test bootstrap**

Create `backend/tests/conftest.py` with minimal shared setup:

```python
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("JWT_SECRET", "test-secret")
```

- [ ] **Step 4: Run the targeted test**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_main.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pytest.ini backend/tests/conftest.py
git commit -m "test: fix backend pytest import path"
```

### Task 2: Add Document Parser Unit

**Files:**
- Create: `backend/app/services/document_parser.py`
- Create: `backend/tests/services/test_document_parser.py`
- Modify: `backend/app/api/endpoints/documents.py`

- [ ] **Step 1: Write the failing parser tests**

Create tests for:
- plain text bytes decode into normalized text
- unsupported binary content raises a parser error
- parser chooses implementation from filename or content type

- [ ] **Step 2: Run parser tests to verify red**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/services/test_document_parser.py -q`
Expected: FAIL because module or functions do not exist

- [ ] **Step 3: Implement minimal parser**

Create `backend/app/services/document_parser.py` with:

```python
from dataclasses import dataclass

@dataclass
class ParsedDocument:
    text: str
    pages: list[str]

class DocumentParseError(Exception):
    pass

def parse_document(file_bytes: bytes, filename: str, content_type: str | None) -> ParsedDocument:
    ...
```

Initial scope:
- support `.txt` and `text/plain`
- reject unsupported file types explicitly
- normalize BOM and newlines

- [ ] **Step 4: Wire upload endpoint to parser**

Replace the current `utf-8` decode fallback in `backend/app/api/endpoints/documents.py` so upload path:
- calls `parse_document`
- returns HTTP 400 for unsupported documents
- sends parsed text into background processing

- [ ] **Step 5: Run parser tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/services/test_document_parser.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/document_parser.py backend/app/api/endpoints/documents.py backend/tests/services/test_document_parser.py
git commit -m "feat: add document parser foundation"
```

### Task 3: Add Structured Chunking Unit

**Files:**
- Modify: `backend/app/services/rag.py`
- Create: `backend/tests/services/test_chunking.py`
- Modify: `backend/tests/services/test_rag.py`

- [ ] **Step 1: Write failing chunking tests**

Create tests for:
- preserving section headers in the same chunk
- splitting long text into stable overlapping chunks
- assigning chunk indexes in order

- [ ] **Step 2: Run chunking tests to verify red**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/services/test_chunking.py -q`
Expected: FAIL because structured chunking helpers do not exist

- [ ] **Step 3: Implement minimal chunk builder**

In `backend/app/services/rag.py`, extract:

```python
def split_document_text(text: str) -> list[str]:
    ...
```

Behavior:
- normalize line endings
- preserve common medical headings
- chunk by paragraphs first, then fallback to length split

- [ ] **Step 4: Refactor process_document to use the chunk builder**

Update `process_document` so it:
- uses `split_document_text`
- generates embeddings from resulting chunks
- keeps existing DB writes unchanged except for better chunk content

- [ ] **Step 5: Update process_document test**

Modify `backend/tests/services/test_rag.py` to assert:
- chunk records are added
- document status becomes `completed`
- the embedding model is called with the chunk list

- [ ] **Step 6: Run chunking and rag tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/services/test_chunking.py backend/tests/services/test_rag.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/rag.py backend/tests/services/test_chunking.py backend/tests/services/test_rag.py
git commit -m "feat: add structured rag chunking"
```

### Task 4: Add Embedding Provider Boundary

**Files:**
- Create: `backend/app/services/embeddings.py`
- Modify: `backend/app/services/rag.py`
- Modify: `backend/app/services/chat.py`
- Create: `backend/tests/services/test_embeddings.py`

- [ ] **Step 1: Write failing provider tests**

Test:
- mock provider returns deterministic vectors
- service lookup returns the configured provider

- [ ] **Step 2: Run provider tests to verify red**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/services/test_embeddings.py -q`
Expected: FAIL because provider module does not exist

- [ ] **Step 3: Implement provider boundary**

Create `backend/app/services/embeddings.py`:

```python
class EmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError
```

Provide:
- `MockEmbeddingProvider`
- `get_embedding_provider()`

- [ ] **Step 4: Replace inline mock classes**

Update `backend/app/services/rag.py` and `backend/app/services/chat.py` to import the provider instead of defining local `MockEmbeddings`.

- [ ] **Step 5: Run provider and related service tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/services/test_embeddings.py backend/tests/services/test_rag.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/embeddings.py backend/app/services/rag.py backend/app/services/chat.py backend/tests/services/test_embeddings.py
git commit -m "refactor: extract embedding provider boundary"
```
