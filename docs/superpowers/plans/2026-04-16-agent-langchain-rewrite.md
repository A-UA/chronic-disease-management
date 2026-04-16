# Agent LangChain Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely rewrite the backend AI Middleware (`agent/` folder) using native LangChain, LangGraph, and LangSmith, replacing the legacy ad-hoc orchestration system. It incorporates natively standard `agentskills.io` skills and uses `uv` for package management.

**Architecture:** A FastAPI wrapper around a LangGraph `StateGraph`. The graph binds native `@tool` and dynamically loaded `StructuredTool` instances (from `agentskills.io` format) to a ChatOpenAI model. RAG is directly handled by `langchain-milvus`. Output is streamed back to the Gateway by consuming LangGraph's asynchronous event streams.

**Tech Stack:** Python 3.12, `uv`, `fastapi`, `langgraph`, `langchain-openai`, `langchain-milvus`, `langsmith`, `pyyaml`.

---

### Task 1: Project Skeleton & `uv` Setup

**Files:**
- Create: `agent/pyproject.toml`
- Create: `agent/app/__init__.py`
- Create: `agent/tests/test_basic.py`

- [ ] **Step 1: Initialize workspace using `uv`**

```bash
mkdir -p agent/tests agent/app
cd agent
uv init --no-workspace
```
*(This ensures standard `pyproject.toml` and `.python-version` files are correctly seeded)*

- [ ] **Step 2: Add essential dependencies with `uv`**

```bash
cd agent
uv add fastapi uvicorn httpx langchain-core langchain-openai langchain-milvus langgraph pyyaml pydantic-settings sse-starlette pydantic tiktoken
uv add --dev pytest pytest-asyncio
```

- [ ] **Step 3: Write basic infrastructure test**

```python
# In agent/tests/test_basic.py
def test_environment_initialized():
    import fastapi
    import langgraph
    import langchain_core
    assert fastapi is not None
    assert langgraph is not None
    assert langchain_core is not None
```

- [ ] **Step 4: Run the test to verify**

```bash
cd agent
uv run pytest tests/test_basic.py
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/
git commit -m "chore(agent): initialize fresh project using uv and install langgraph stack"
```

---

### Task 2: Environment Configuration Base

**Files:**
- Create: `agent/app/config.py`
- Create: `agent/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# In agent/tests/test_config.py
import os
from app.config import settings

def test_settings_load():
    os.environ["MILVUS_HOST"] = "test-host"
    os.environ["GATEWAY_URL"] = "http://localhost:8080"
    
    assert settings.model_dump() is not None
    assert "MILVUS_HOST" in settings.model_fields
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent ; uv run pytest tests/test_config.py`
Expected: FAIL (ModuleNotFoundError: No module named 'app.config')

- [ ] **Step 3: Write minimal implementation**

```python
# In agent/app/config.py
from pydantic_settings import BaseSettings

class AgentSettings(BaseSettings):
    GATEWAY_URL: str = "http://host.docker.internal:8080"
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_PREFIX: str = "cdm_"
    CHAT_MODEL: str = "gpt-4o-mini"
    
    # Langsmith config is automatically fetched from OS ENV by Langchain (LANGCHAIN_TRACING_V2, etc)
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = AgentSettings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent ; uv run pytest tests/test_config.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/app/config.py agent/tests/test_config.py
git commit -m "feat(agent): implement pydantic environment settings"
```

---

### Task 3: AgentSkills Standard Loader (`SKILL.md`)

**Files:**
- Create: `agent/app/agent/tools/markdown_loader.py`
- Create: `agent/tests/test_markdown_loader.py`
- Create: `agent/skills/example/SKILL.md`

- [ ] **Step 1: Write mock SKILL.md file**

```markdown
# In agent/skills/example/SKILL.md
---
name: example_skill
description: An example standard agent skill
---
You are an expert. Respond specifically using example knowledge.
```

- [ ] **Step 2: Write the failing test**

```python
# In agent/tests/test_markdown_loader.py
import os
from pathlib import Path
from app.agent.tools.markdown_loader import load_skills_from_directory

def test_load_skills(tmp_path):
    d = tmp_path / "test_skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: my_test\ndescription: test desc\n---\nbody text")
    
    tools = load_skills_from_directory(str(tmp_path))
    assert len(tools) == 1
    assert tools[0].name == "my_test"
    assert tools[0].description == "test desc"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd agent ; uv run pytest tests/test_markdown_loader.py`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 4: Write minimal implementation**

```python
# In agent/app/agent/tools/markdown_loader.py
import os
from pathlib import Path
import yaml
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class GenericSkillInput(BaseModel):
    query: str = Field(description="The contextual query for this skill to act upon")

def markdown_skill_factory(name: str, description: str, instructions: str):
    def _run_skill(query: str) -> str:
        # In a real environment, we'd invoke sub-chains, 
        # but the standard agentskills.io way passes instructions as context back to the agent:
        return f"=== SKILL INSTRUCTIONS ===\n{instructions}\n=== END SKILL/APPLY TO ===\nQuery: {query}"
        
    return StructuredTool.from_function(
        func=_run_skill,
        name=name,
        description=description,
        args_schema=GenericSkillInput
    )

def load_skills_from_directory(directory: str) -> list[StructuredTool]:
    tools = []
    base_path = Path(directory)
    if not base_path.exists():
        return tools
        
    for skill_dir in base_path.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                    tools.append(
                        markdown_skill_factory(
                            name=frontmatter.get("name", skill_dir.name),
                            description=frontmatter.get("description", ""),
                            instructions=body
                        )
                    )
    return tools
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent ; uv run pytest tests/test_markdown_loader.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent/
git commit -m "feat(agent): implement dynamic agentskills.io markdown tool loader"
```

---

### Task 4: Milvus RAG Tool 

**Files:**
- Create: `agent/app/agent/tools/rag_tool.py`
- Create: `agent/tests/test_rag_tool.py`

- [ ] **Step 1: Write the failing test**

```python
# In agent/tests/test_rag_tool.py
from app.agent.tools.rag_tool import rag_search_handler

def test_rag_search_handler():
    # It should be a standard LangChain Tool
    assert hasattr(rag_search_handler, "name")
    assert rag_search_handler.name == "rag_search"
    assert "query" in rag_search_handler.args
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent ; uv run pytest tests/test_rag_tool.py`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
# In agent/app/agent/tools/rag_tool.py
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from app.config import settings

@tool
def rag_search_handler(query: str, kb_id: int) -> str:
    """在知识库中检索与问题相关的文档内容，返回带引用的上下文"""
    embeddings = OpenAIEmbeddings()
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,
    )
    
    # Restrict by kb_id
    search_kwargs = {"expr": f"kb_id == {kb_id}"}
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    
    docs = retriever.invoke(query)
    if not docs:
        return "该知识库中未找到与提问最相关的内容。"
    
    # Format and return references
    context = "\n\n".join([f"[引用] {doc.page_content}" for doc in docs])
    return context
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent ; uv run pytest tests/test_rag_tool.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/
git commit -m "feat(agent): add milvus rag tool utilizing langchain_milvus"
```

---

### Task 5: Core LangGraph Agent Assembly

**Files:**
- Create: `agent/app/agent/graph.py`
- Create: `agent/tests/test_graph.py`

- [ ] **Step 1: Write the failing test**

```python
# In agent/tests/test_graph.py
from app.agent.graph import create_agent_graph

def test_graph_creation():
    graph = create_agent_graph()
    assert graph is not None
    assert "assistant" in graph.nodes
    assert "tools" in graph.nodes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent ; uv run pytest tests/test_graph.py`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
# In agent/app/agent/graph.py
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.agent.tools.markdown_loader import load_skills_from_directory
from app.agent.tools.rag_tool import rag_search_handler

def create_agent_graph():
    # Load default tools
    SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
    md_tools = []
    if SKILLS_DIR.exists():
        md_tools = load_skills_from_directory(str(SKILLS_DIR))
        
    tools = md_tools + [rag_search_handler]
    
    llm = ChatOpenAI(model=settings.CHAT_MODEL).bind_tools(tools)
    
    # Use ToolNode for standard tool invocation fallback
    tool_node = ToolNode(tools)
    
    def assistant_node(state: MessagesState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content="你是慢病管理的 AI 助手。必须使用中文回答。")] + messages
        response = llm.invoke(messages)
        return {"messages": [response]}
        
    builder = StateGraph(MessagesState)
    builder.add_node("assistant", assistant_node)
    builder.add_node("tools", tool_node)
    
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)
    builder.add_edge("tools", "assistant")
    
    return builder.compile()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent ; uv run pytest tests/test_graph.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/
git commit -m "feat(agent): construct core messages state graph via langgraph"
```

---

### Task 6: FastAPI Runtime Integration

**Files:**
- Create: `agent/app/routers/internal.py`
- Create: `agent/app/main.py`
- Create: `agent/tests/test_main.py`

- [ ] **Step 1: Write the failing test**

```python
# In agent/tests/test_main.py
from fastapi.testclient import TestClient
from app.main import app

def test_fastapi_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent ; uv run pytest tests/test_main.py`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
# In agent/app/routers/internal.py
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from typing import Any
from app.agent.graph import create_agent_graph

internal_router = APIRouter(prefix="/internal")
graph = create_agent_graph()

class ChatRequest(BaseModel):
    query: str
    metadata: dict[str, Any] = {}

@internal_router.post("/chat")
async def chat_stream(req: ChatRequest):
    async def event_generator():
        messages = [HumanMessage(content=req.query)]
        # We use standard astream_events pattern
        async for event in graph.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield {"event": "message", "data": chunk.content}
            # Add other tools/logging events naturally mapped for SSE...
                    
    return EventSourceResponse(event_generator())

@internal_router.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    messages = [HumanMessage(content=req.query)]
    response = await graph.ainvoke({"messages": messages})
    return {"reply": response["messages"][-1].content}
```

```python
# In agent/app/main.py
from fastapi import FastAPI
from app.routers.internal import internal_router

app = FastAPI(title="CDM Agent Middleware")
app.include_router(internal_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent ; uv run pytest tests/test_main.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/
git commit -m "feat(agent): establish fastapi endpoint layer for langgraph stream"
```
