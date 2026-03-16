# Manager Workbench Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement core manager features: viewing assigned patients and writing management suggestions.

**Architecture:** Extend the manager model with a suggestions table and provide specialized API endpoints for clinical workflow.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (Async), Alembic, PostgreSQL RLS.

---

## Chunk 1: Database & Models

### Task 1: Add ManagementSuggestion Model
**Files:**
- Modify: `app/db/models/manager.py`
- Modify: `app/db/models/__init__.py`

- [ ] **Step 1: Define ManagementSuggestion class**
Add `ManagementSuggestion` to `app/db/models/manager.py` (patient_id, manager_id, org_id, content, suggestion_type).
- [ ] **Step 2: Generate Alembic migration**
`uv run alembic revision --autogenerate -m "add_management_suggestions"`
- [ ] **Step 3: Add RLS policy to migration**
Enable RLS and add isolation policy for `management_suggestions`.
- [ ] **Step 4: Execute migration**
`uv run alembic upgrade head`
- [ ] **Step 5: Commit**
`git commit -m "feat: add management_suggestions model and RLS"`

## Chunk 2: API Development

### Task 2: Implement Manager Endpoints
**Files:**
- Create: `app/api/endpoints/managers.py`
- Modify: `app/api/api.py`

- [ ] **Step 1: Implement GET /patients**
List patients assigned to current manager.
- [ ] **Step 2: Implement POST /patients/{patient_id}/suggestions**
Create a new clinical suggestion. Ensure manager is assigned to patient.
- [ ] **Step 3: Implement GET /patients/{patient_id}/suggestions**
List history of suggestions for a patient.
- [ ] **Step 4: Register router**
Update `app/api/api.py`.
- [ ] **Step 5: Verify with integration test**
Simulate Manager login -> Get assigned patients -> Write suggestion.
- [ ] **Step 6: Commit**
`git commit -m "feat: implement manager workbench APIs"`
