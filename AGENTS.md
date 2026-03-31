# AGENTS.md — Repository Guidelines

## Project Overview

Multi-tenant AI SaaS for chronic disease management with a RAG (Retrieval-Augmented Generation) core.

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy 2.x async, PostgreSQL + pgvector
- **Frontend**: UmiJS Max 4, Ant Design Pro, TypeScript, React 18
- **Infra**: Docker Compose (Postgres, Redis, MinIO), uv (Python), pnpm (Node)

## Quick Reference — Commands

### Backend (`backend/`)

```bash
cd backend

# Install / sync dependencies
uv sync

# Start dev server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
uv run python -m pytest

# Run a single test file
uv run python -m pytest tests/services/test_chat.py

# Run a single test by name
uv run python -m pytest tests/services/test_chat.py -k test_ranked_chunks_fusion_and_sources

# Database migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
```

### Frontend (`frontend/`)

```bash
cd frontend

# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Lint
pnpm lint

# Type check
pnpm tsc

# Production build
pnpm build
```

### Docker

```bash
docker compose up -d    # Start Postgres, Redis, MinIO
```

## Testing Conventions

- **Framework**: pytest + pytest-asyncio (`asyncio_mode = auto` in `pytest.ini`)
- Tests live in `backend/tests/`, mirroring `app/` structure: `tests/api/`, `tests/services/`
- Use `@pytest.mark.asyncio` on async test functions (redundant with auto mode but explicit)
- Mock external services (LLM, embedding, Redis) with `unittest.mock.AsyncMock` / `MagicMock`
- API integration tests use `httpx.AsyncClient` with `ASGITransport` against a local FastAPI app
- Use `conftest.py` for shared fixtures; set `JWT_SECRET` env var before imports

## Backend Code Style

### Imports

- Standard library → third-party → local (`app.`) — separated by blank lines
- Use `from __future__ import annotations` when forward references are needed
- Guard heavy imports with `if TYPE_CHECKING:` for type-only dependencies
- Do **not** initialize external services at import time

### Types & Models

- All new DB tables must use `IDMixin` (Snowflake BigInteger primary key)
- ID fields are typed as `int` in Python; the `SnowflakeJSONResponse` handles JS precision at the API layer
- Use SQLAlchemy 2.x `Mapped[...]` / `mapped_column(...)` style
- Pydantic schemas in `app/schemas/` for request/response validation
- Use `TypedDict` or `@dataclass(slots=True)` for internal service data structures

### Naming

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions / variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Pydantic / TypedDict fields: `snake_case`

### Async Patterns

- All DB access is async via `AsyncSession`
- Use `async def` for all route handlers and service functions touching I/O
- Use `select()` construct (SQLAlchemy 2.x style), not legacy `session.query()`
- Inject DB session via FastAPI `Depends(get_db)`

### Error Handling

- Raise `HTTPException` with appropriate status codes in API layer
- Service functions should raise domain exceptions or let errors propagate
- Global exception middleware in `main.py` catches unhandled errors (returns 500)
- Never expose internal stack traces to clients

### API Design

- Versioned prefix: `/api/v1/`
- Multi-tenancy via `X-Organization-ID` header (optional, falls back to user's first org)
- Auth via JWT Bearer tokens; use `Depends(get_current_user)` / `Depends(get_current_org_user)`
- Permission checks via `Depends(check_permission("code"))`
- Prefer provider / service abstraction for new features

## Frontend Code Style

- TypeScript strict mode enabled
- Path alias: `@/*` → `src/*`
- Pages in `src/pages/`, services in `src/services/`, shared components in `src/components/`
- Use `@umijs/max` APIs: `history`, `useModel`, `useAccess`, `request`
- Ant Design 5 components; prefer `ProTable`, `ProForm` from `@ant-design/pro-components`
- Auth token stored in `localStorage('token')`; org context in `localStorage('currentOrgId')`
- Request interceptor auto-attaches `Authorization` and `X-Organization-ID` headers

## Key Architectural Notes

- **RAG pipeline**: document parsing → ingestion → hybrid retrieval (vector + keyword) → rerank → LLM with citations
- **Serialization**: `orjson` via custom `SnowflakeJSONResponse`; large integers auto-converted to strings
- **Provider pattern**: LLM, embedding, and reranker implementations are swappable via `provider_registry`
- **RLS**: Row-level security context injected per-request via `set_config('app.current_org_id', ...)`
- **Caching**: Redis for retrieval cache and rate limiting; falls back to DB on miss
