# Agent Knowledge Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `/internal/knowledge/parse` endpoint to accept file uploads, chunk text, and insert into Milvus.

**Architecture:** We will add `python-multipart` as a dependency, build a modular `ingestion.py` in the `agent` package to do LangChain text splitting and Milvus embedding, and wire an upload endpoint onto `internal_router`.

**Tech Stack:** Python, FastAPI (UploadFile), LangChain (`RecursiveCharacterTextSplitter`), Milvus, Pytest

---

### Task 1: Add Dependencies

**Files:**
- Modify: `agent/pyproject.toml`
- Test: (Terminal Check)

- [ ] **Step 1: Add python-multipart to dependencies**

Modify `agent/pyproject.toml` to add `python-multipart>=0.0.9`. It should be placed under the `dependencies` block.

```toml
dependencies = [
    "fastapi>=0.135.3",
    "httpx>=0.28.1",
    "langchain-core>=1.2.30",
    "langchain-milvus>=0.3.3",
    "langchain-openai>=1.1.13",
    "langgraph>=1.1.6",
    "pydantic>=2.13.1",
    "pydantic-settings>=2.13.1",
    "python-multipart>=0.0.9",
    "pyyaml>=6.0.3",
    "sse-starlette>=3.3.4",
    "tiktoken>=0.12.0",
    "uvicorn>=0.44.0",
]
```

- [ ] **Step 2: Sync dependencies**

Run: `cd agent; uv sync`
Expected: Success, dependencies linked.

- [ ] **Step 3: Commit**

```bash
git add agent/pyproject.toml agent/uv.lock
git commit -m "build(agent): 增加 python-multipart 依赖处理文件上传"
```

### Task 2: Implement Ingestion Logic

**Files:**
- Create: `agent/tests/test_ingestion.py`
- Create: `agent/app/agent/ingestion.py`

- [ ] **Step 1: Write the failing test**

Create `agent/tests/test_ingestion.py`:
```python
from app.agent.ingestion import process_document_to_milvus

def test_process_document_to_milvus(mocker):
    # Mock OpenAiEmbeddings and Milvus to avoid real network calls
    mocker.patch("app.agent.ingestion.OpenAIEmbeddings")
    mock_milvus = mocker.patch("app.agent.ingestion.Milvus")
    
    # Mock the add_documents instance method
    mock_instance = mock_milvus.return_value
    mock_instance.add_documents.return_value = ["id1", "id2"]
    
    file_bytes = "Test line 1.\nTest line 2.".encode("utf-8")
    chunk_count = process_document_to_milvus(file_bytes, "test.txt", "kb_123")
    
    assert chunk_count > 0
    mock_instance.add_documents.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent; uv run pytest tests/test_ingestion.py`
Expected: Error because `app.agent.ingestion` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `agent/app/agent/ingestion.py`:
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from app.config import settings

def process_document_to_milvus(file_bytes: bytes, filename: str, kb_id: str) -> int:
    text_content = file_bytes.decode('utf-8', errors='ignore')
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    texts = splitter.split_text(text_content)
    
    docs = [
        Document(
            page_content=txt,
            metadata={"kb_id": kb_id, "filename": filename, "source": filename}
        )
        for txt in texts
    ]
    
    if not docs:
        return 0

    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY
    )
    
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,
    )
    
    vector_store.add_documents(docs)
    return len(docs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent; uv run pytest tests/test_ingestion.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/app/agent/ingestion.py agent/tests/test_ingestion.py
git commit -m "feat(agent): 实现文件解析切割并灌入 Milvus 向量数据库"
```

### Task 3: Implement Internal File Upload API

**Files:**
- Create: `agent/tests/test_knowledge_api.py`
- Modify: `agent/app/routers/internal.py`

- [ ] **Step 1: Write the failing test**

Create `agent/tests/test_knowledge_api.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_knowledge_parse_upload(mocker):
    # Mock the ingestion process
    mocker.patch("app.routers.internal.process_document_to_milvus", return_value=3)
    
    response = client.post(
        "/internal/knowledge/parse",
        data={"kb_id": "kb_test_01"},
        files={"file": ("sample.txt", b"Hello knowledge", "text/plain")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["chunk_count"] == 3
    assert data["filename"] == "sample.txt"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent; uv run pytest tests/test_knowledge_api.py`
Expected: FAIL with 404 (route not found).

- [ ] **Step 3: Write minimal implementation**

Modify `agent/app/routers/internal.py`. 

Add to imports at the top:
```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.agent.ingestion import process_document_to_milvus
```

Add the route at the end of the file:
```python
@internal_router.post("/knowledge/parse")
async def parse_knowledge_document(
    file: UploadFile = File(...),
    kb_id: str = Form(...)
):
    try:
        content = await file.read()
        chunk_count = process_document_to_milvus(content, file.filename, kb_id)
        return {
            "status": "success",
            "filename": file.filename,
            "chunk_count": chunk_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent; uv run pytest tests/test_knowledge_api.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/app/routers/internal.py agent/tests/test_knowledge_api.py
git commit -m "feat(agent): 暴露 /internal/knowledge/parse 接口供网关上传解析调用"
```
