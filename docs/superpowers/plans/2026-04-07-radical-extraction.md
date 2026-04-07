# BFF Gateways & AI Engine Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract agent and rag to `app/engine` and physically merge 20+ scattered FastAPI routers into 4 core Gateway files.
**Architecture:** Hexagonal Architecture (Ports and Adapters). Core logic resides in `engine` and `modules`. HTTP resides entirely in `api/gateways`.
**Tech Stack:** FastAPI, Python, Pytest, Ruff

---

### Task 1: Extract AI Engine Core
**Files:**
- Modify: Move `app/modules/rag` to `app/engine/rag`
- Modify: Move `app/modules/agent` to `app/engine/agent`

- [ ] **Step 1: Move directories via shell**
```powershell
mkdir app/engine
Move-Item -Path app/modules/rag -Destination app/engine/
Move-Item -Path app/modules/agent -Destination app/engine/
```

- [ ] **Step 2: Initialize engine module**
```powershell
Out-File -FilePath app/engine/__init__.py -Encoding utf8
```

### Task 3: Migrate Auth Gateway (1-to-1 mapping)
**Files:**
- Create: `app/api/gateways/auth_api.py`
- Delete: `app/modules/auth/router.py`

- [ ] **Step 1: Move and rename file**
```powershell
mkdir -Force app/api/gateways
Move-Item -Path app/modules/auth/router.py -Destination app/api/gateways/auth_api.py
```

### Task 4: Construct AI Gateway (Merge 4 into 1)
**Files:**
- Create: `app/api/gateways/ai_api.py`
- Delete: `app/engine/rag/router_chat.py`, `router_documents.py`, `router_knowledge_bases.py`, `router_conversations.py`

- [ ] **Step 1: Subagent reads the 4 source files to understand their contents.**
- [ ] **Step 2: Subagent consolidates the logic into `app/api/gateways/ai_api.py`.**
  - Combine all `import` statements at the top.
  - Define a single `router = APIRouter()`.
  - Copy all route definitions (`@router.post(...)`) sequentially.
- [ ] **Step 3: Subagent executes file creation and validates format via Ruff.**
```powershell
uv run ruff check --fix app/api/gateways/ai_api.py
```
- [ ] **Step 4: Delete old files**
```powershell
Remove-Item app/engine/rag/router_chat.py, app/engine/rag/router_documents.py, app/engine/rag/router_knowledge_bases.py, app/engine/rag/router_conversations.py
```

### Task 5: Construct Clinic Gateway (Merge Patient Routers)
**Files:**
- Create: `app/api/gateways/clinic_api.py`
- Delete: `app/modules/patient/router_patients.py`, `router_health_metrics.py`, `router_family.py`, `router_managers.py`

- [ ] **Step 1: Subagent reads the 4 source files to understand their contents.**
- [ ] **Step 2: Subagent consolidates the logic into `app/api/gateways/clinic_api.py`.**
- [ ] **Step 3: Format and fix**
```powershell
uv run ruff check --fix app/api/gateways/clinic_api.py
```
- [ ] **Step 4: Delete old files**
```powershell
Remove-Item app/modules/patient/router_patients.py, app/modules/patient/router_health_metrics.py, app/modules/patient/router_family.py, app/modules/patient/router_managers.py
```

### Task 6: Construct Admin Gateway (Merge System & Audit Routers)
**Files:**
- Create: `app/api/gateways/admin_api.py`
- Delete: All `router_*.py` in `modules/system/` and `modules/audit/router.py`

- [ ] **Step 1: Subagent reads all source files.**
- [ ] **Step 2: Subagent consolidates the logic into `app/api/gateways/admin_api.py`.**
- [ ] **Step 3: Format and fix**
```powershell
uv run ruff check --fix app/api/gateways/admin_api.py
```
- [ ] **Step 4: Delete old files**
```powershell
Remove-Item app/modules/system/router_*.py
Remove-Item app/modules/audit/router.py
```

### Task 7: Rewire Master Router (`app/api/api.py`)
**Files:**
- Modify: `app/api/api.py`

- [ ] **Step 1: Update API Router to use only the 4 new gateways**
```python
from fastapi import APIRouter

from app.api.gateways import (
    auth_api,
    admin_api,
    clinic_api,
    ai_api
)

api_router = APIRouter()

api_router.include_router(auth_api.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin_api.router, prefix="/system", tags=["System & Admin"])
api_router.include_router(clinic_api.router, tags=["Clinical & Patients"])
api_router.include_router(ai_api.router, prefix="/ai", tags=["AI Engine"])
```

### Task 8: Global Import Resolution
**Files:**
- Modify: Multiple `tests/` and service files across the codebase.

- [ ] **Step 1: Run pytest to reveal broken import paths due to moved files.**
```powershell
uv run pytest
```
- [ ] **Step 2: Fix any `ModuleNotFoundError` or mock path errors iteratively.**
  Identify references like `app.modules.rag...` and change to `app.engine.rag...`.
  Identify test mocks that patch old router paths and update them to `app.api.gateways...`.

- [ ] **Step 3: Enforce final Ruff linting on entire app.**
```powershell
uv run ruff check --fix app/
```
