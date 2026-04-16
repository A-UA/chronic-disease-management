# Agent Middleware Rewrite (LangChain + LangGraph + LangSmith) Design Spec

## 1. Overview
The legacy `agent` AI middleware layer has been entirely discarded. The goal is to build a greenfield application that uses native `langchain`, `langgraph`, and `langsmith` for orchestration, telemetry, and observability. This service will act as a thin intelligent middleware between the user's chat interface (via the Java/NestJS API Gateway) and the downstream microservices, specifically integrating standard `agentskills.io` formatted Markdown skills and an explicit Milvus RAG retriever.

## 2. Architecture & Tech Stack

- **Framework**: `FastAPI` (Thin wrapper).
- **Orchestration**: `langgraph.graph.StateGraph` & `MessagesState`.
- **LLM/Embeddings**: `langchain-openai` (compatible with external providers like ZhiPu or local MiMo models via configurable Base URLs).
- **VectorStore**: `langchain-milvus` (Official wrapper for Milvus).
- **Tools / Skills Standard**: Native LangChain `@tool` & dynamic injection of `agentskills.io` `SKILL.md` structures into `StructuredTool`.
- **Telemetry**: Pure `LangSmith` Tracing (`LANGCHAIN_TRACING_V2=true`).

## 3. Directory Layout (Proposed)

```text
agent/
├── app/
│   ├── main.py                     # FastAPI initiation & LangChain dependency check
│   ├── config.py                   # Pydantic BaseSettings (Gateway URL, Milvus URI, API Keys)
│   ├── agent/
│   │   ├── graph.py                # LangGraph definition: Nodes & Edges (assistant_node, tools_condition)
│   │   └── tools/                  
│   │       ├── api_tools.py        # Gateway REST interaction tools (httpx)
│   │       ├── rag_tool.py         # langchain-milvus retriever wrapped as a @tool
│   │       └── markdown_loader.py  # agentskills.io SKILL.md parsing to LangChain tools
│   └── routers/
│       └── internal.py             # FastAPI routes: POST /internal/chat (astream_events), /chat/sync, /ingest
├── skills/                         # agentskills.io standard storage folder
│   └── ...                         # User-defined SKILL.md rules and references
└── requirements.txt / pyproject.toml 
```

## 4. Key Components Design

### 4.1 FastAPI Endpoints
Routes conform to the internal microservices signature, trusting downstream API gateways. Auth tokens (`X-Identity-Base64`, `Authorization`) are extracted from `Request.headers` and placed into LangChain `RunnableConfig` for transparent propagation.

- **`/internal/chat`**: Implements Async Server-Sent Events (SSE) by consuming `AgentGraph.astream_events(...)` and formatting into standardized chunks.
- **`/internal/chat/sync`**: Directly relies on `AgentGraph.ainvoke(...)`.
- **`/internal/ingest`**: Exposes PDF parsing and ingestion into `Milvus` using `langchain_text_splitters` and `langchain_milvus.Milvus`.

### 4.2 LangGraph Implementation
The agent logic leverages `StateGraph` over `MessagesState`. 

- **Assistant Node**: Invokes `llm.bind_tools(tools)`. It consumes the entire message array + injected contexts dynamically.
- **Tools Node**: Employs `langgraph.prebuilt.ToolNode(tools)` for strictly standard execution schema and reliable fallback.

### 4.3 RAG via `langchain-milvus`
Replacing custom RAG algorithms, the `Rag Tool` leverages `Milvus(..., embedding_function=...).as_retriever()`. This makes retrieval seamlessly embedded within vector search constraints (kb_id routing), while simplifying the code footprint.

### 4.4 AgentSkills Standard Loader
Implementation of `app/agent/tools/markdown_loader.py`.
- **Discovery**: Traverses `agent/skills/`.
- **Parsing**: Separates `YAML frontmatter` (extracting `name`, `description`, `required_params`) and the `Markdown Body`.
- **Registration**: Emits `langchain_core.tools.StructuredTool.from_function()` artifacts that trigger predefined prompt enhancements or execute shell/Python scripts per the standard guidelines.

## 5. Telemetry & Quota Update Hand-offs
Instead of custom Opentelemetry `@trace_span` blocks and raw PostgreSQL queries to calculate tokens:
1. `LangSmith` natively logs token utilizations, latency distributions, and the chain of thought.
2. The endpoint returns `token_count` transparently (fetched from LangChain's callback handler or standard `response_metadata`), enabling the upstream Gateway API to enforce robust RateLimiting and Usage Quota charging.

## 6. Development Workflow Plan
1. Project Initialization & Dependencies (FastAPI + LangChain + LangGraph + Milvus + HTTpx).
2. Environment Configuration Base (`config.py`).
3. Core Agent Graph creation (`graph.py`, standard ToolNode bindings).
4. `agentskills.io` standard loader & Gateway Integration Tools (`tools/`).
5. `langchain-milvus` integration implementation (`rag_tool.py` and `internal/ingest`).
6. FastAPI Routes wiring & Integration validation.
