# Multi-Tenant AI SaaS Backend (GEMINI.md)

## 1. Project Overview

This is the backend repository for a high-performance multi-tenant AI SaaS platform. It centers around RAG (Retrieval-Augmented Generation) capabilities, supporting multi-organization management, role-based access control (RBAC), and usage billing/tracking.

### Key Implemented Features:
- **FastAPI Async Architecture**: Non-blocking request handling with `asyncpg`.
- **Row-Level Security (RLS)**: Enforced multi-tenant isolation directly at the PostgreSQL level.
- **Quota & Rate Limiting**: Redis-backed (asynchronous) rate limiting and atomic token quota management.
- **RAG Pipeline**: Background document processing (splitting, embedding, and storage).
- **Streaming Support**: Server-Sent Events (SSE) for real-time AI responses with metadata.

## 2. Directory Structure
...

- `app/`: Core backend application code
  - `api/`: API routing and dependency injection (`deps.py` for auth and tenant context)
  - `core/`: Global configurations, settings, and security
  - `db/`: Database models (`models/`) and session management
  - `services/`: Business logic including RAG processing, chat generation, quota tracking, and storage
- `alembic/` & `alembic.ini`: Database migration scripts and configuration
- `docs/superpowers/`: Detailed design specifications and implementation plans
- `tests/`: Automated test suite using `pytest` covering APIs and services
- `docker-compose.yml`: Infrastructure definitions for PostgreSQL (+pgvector), Redis, and MinIO
- `pyproject.toml`: Python project metadata and dependencies

## 3. Building and Running

### 3.1 Infrastructure

Start the required external services (PostgreSQL, Redis, MinIO) using Docker:

```bash
docker compose up -d
```

### 3.2 Backend Development Environment

1. **Install dependencies** (using `uv` is recommended):
   ```bash
   uv sync
   ```

2. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Start the application**:
   ```bash
   uvicorn app.main:app --reload
   ```
   API documentation (Swagger UI) is typically available at `/docs` or `/api/v1/docs`.

### 3.3 Running Tests

Run the full test suite utilizing `pytest-asyncio`:

```bash
pytest
```

## 4. Development Conventions & Best Practices

- **Multi-Tenant Context**: 
  - API requests interacting with tenant data require specifying the current organization (e.g., via `X-Organization-Id` headers or parsed from the API key).
  - Row-Level Security (RLS) should be applied at the database level by setting the `app.current_org_id` context in the database session.
- **Database Operations**:
  - Always use asynchronous sessions (`AsyncSession`) for all database operations.
  - Data models must inherit from `app.db.models.base.Base` and explicitly include an `org_id` field if the entity belongs to a specific tenant.
- **RAG & Streaming APIs**:
  - All streaming responses (e.g., chat completions) should be implemented using Server-Sent Events (SSE).
- **Authentication**:
  - Use JWT Bearer Tokens for user authentication and scoped API Keys for external integrations.
- **Testing**:
  - Always add unit or integration tests in the `tests/` directory for new endpoints and business logic.
