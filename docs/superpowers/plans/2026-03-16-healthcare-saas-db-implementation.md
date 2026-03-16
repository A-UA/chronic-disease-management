# Healthcare SaaS DB Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the specialized database models for patients, managers, and family members with RLS-backed multi-tenant isolation.

**Architecture:** Hybrid multi-tenant schema where patients/managers are tied to orgs, and family members access patient data through dynamic authorization links.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (Async), Alembic, PostgreSQL RLS.

---

## Chunk 1: Models & Migrations

### Task 1: Create Domain Models
**Files:**
- Create: `app/db/models/patient.py`
- Create: `app/db/models/manager.py`
- Modify: `app/db/models/organization.py`
- Modify: `app/db/models/__init__.py`

- [ ] **Step 1: Define PatientProfile model**
Create `app/db/models/patient.py` with `PatientProfile` linked to `User` and `Organization`.
- [ ] **Step 2: Define Manager and Assignment models**
Create `app/db/models/manager.py` with `ManagerProfile` and `PatientManagerAssignment`.
- [ ] **Step 3: Define Family Link model**
Add `PatientFamilyLink` to `app/db/models/organization.py`.
- [ ] **Step 4: Export all new models**
Update `app/db/models/__init__.py`.
- [ ] **Step 5: Generate and run migrations with RLS**
Run autogenerate, then manually inject `ENABLE ROW LEVEL SECURITY` into the migration script for the new tables.
- [ ] **Step 6: Commit**
`git commit -m "feat: add healthcare domain models and RLS migrations"`

## Chunk 2: API & Logic

### Task 2: Implement Patient and Family APIs
**Files:**
- Create: `app/api/endpoints/patients.py`
- Create: `app/api/endpoints/family.py`
- Modify: `app/api/api.py`

- [ ] **Step 1: Implement Patient CRUD**
Create endpoints for patient profile management.
- [ ] **Step 2: Implement Family Linking logic**
Create endpoints for managing family authorizations.
- [ ] **Step 3: Register routers**
Update `api_router` in `app/api/api.py`.
- [ ] **Step 4: Verify with integration test**
Add a new scenario to `tests/integration_test.py` covering the family-patient link.
- [ ] **Step 5: Commit**
`git commit -m "feat: implement healthcare API endpoints"`
