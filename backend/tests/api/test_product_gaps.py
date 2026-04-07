"""产品补全测试

覆盖：管理建议患者可见、管理师解绑、家属解绑、租户用量、组织编辑
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import (
    override_deps, MockScalarResult, PatchRBAC, make_user,
    TENANT_ID, ORG_ID, USER_ID,
)


# ─── 管理建议患者可见 ───

class TestPatientViewSuggestions:
    def _make_app(self):
        from app.modules.patient.router_patients import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/patients")
        return app

    @pytest.mark.asyncio
    async def test_patient_sees_suggestions(self):
        app = self._make_app()
        patient = MagicMock()
        patient.id = 4001
        patient.user_id = USER_ID
        patient.org_id = ORG_ID

        suggestion = MagicMock()
        suggestion.id = 8001
        suggestion.content = "建议每天监测血压"
        suggestion.suggestion_type = "clinical"
        suggestion.manager_id = 1002
        suggestion.patient_id = 4001
        suggestion.created_at = "2026-04-01T00:00:00"

        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[patient]),
            MockScalarResult(items=[suggestion]),
        ]
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/patients/me/suggestions")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    @pytest.mark.asyncio
    async def test_empty_suggestions(self):
        app = self._make_app()
        patient = MagicMock()
        patient.id = 4001
        patient.user_id = USER_ID
        patient.org_id = ORG_ID

        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[patient]),
            MockScalarResult(items=[]),
        ]
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/patients/me/suggestions")
        assert r.status_code == 200
        assert r.json() == []


# ─── 管理师取消分配 ───

class TestManagerUnassign:
    def _make_app(self):
        from app.modules.patient.router_managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    async def test_unassign_ok(self):
        app = self._make_app()
        db = AsyncMock()
        db.execute.return_value = MagicMock(rowcount=1)
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.delete("/api/v1/managers/assignments/4001")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_unassign_not_found_404(self):
        app = self._make_app()
        db = AsyncMock()
        db.execute.return_value = MagicMock(rowcount=0)
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.delete("/api/v1/managers/assignments/99999")
        assert r.status_code == 404


# ─── 家属解绑 ───

class TestFamilyUnlink:
    def _make_app(self):
        from app.modules.patient.router_family import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/family")
        return app

    @pytest.mark.asyncio
    async def test_unlink_ok(self):
        app = self._make_app()
        link = MagicMock()
        link.patient_id = 4001
        link.family_user_id = USER_ID

        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[link])
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.delete("/api/v1/family/links/4001")
        assert r.status_code == 200
        db.delete.assert_called_once_with(link)


# ─── 租户用量自查 ───

class TestTenantUsage:
    def _make_app(self):
        from app.modules.system.router_usage import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/usage")
        return app

    @pytest.mark.asyncio
    async def test_my_org_usage(self):
        app = self._make_app()
        tenant = MagicMock()
        tenant.quota_tokens_limit = 1000000
        tenant.quota_tokens_used = 12500

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar=MagicMock(return_value=12500))
        db.get.return_value = tenant
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/usage/my-org")
        assert r.status_code == 200
        assert "total_tokens" in r.json()


# ─── 组织信息编辑 ───

class TestOrgUpdate:
    def _make_app(self):
        from app.modules.system.router_organizations import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/organizations")
        return app

    @pytest.mark.asyncio
    async def test_update_org_name(self):
        app = self._make_app()
        org = MagicMock()
        org.id = ORG_ID
        org.name = "旧名称"
        org.plan_type = "free"
        org.created_at = "2026-01-01T00:00:00"
        org.parent_id = None
        org.tenant_id = TENANT_ID

        db = AsyncMock()
        db.get.return_value = org
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.put(f"/api/v1/organizations/{ORG_ID}", json={"name": "新名称"})
        assert r.status_code == 200
        assert org.name == "新名称"
