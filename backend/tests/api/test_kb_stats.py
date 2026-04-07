"""知识库统计信息测试

覆盖：正常统计、空知识库、跨租户隔离、404
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import override_deps, TENANT_ID, ORG_ID


def _make_app():
    from app.modules.rag.router_knowledge_bases import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/kb")
    return app


def _kb(kb_id=3001, tenant_id=TENANT_ID, org_id=ORG_ID):
    k = MagicMock()
    k.id = kb_id
    k.tenant_id = tenant_id
    k.org_id = org_id
    k.name = "测试知识库"
    k.description = "描述"
    k.created_at = "2026-01-01T00:00:00"
    return k


class TestKBStats:
    @pytest.mark.asyncio
    async def test_returns_stats(self):
        app = _make_app()
        kb = _kb()
        db = AsyncMock()
        db.get.return_value = kb
        db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=5)),
            MagicMock(scalar=MagicMock(return_value=120)),
            MagicMock(scalar=MagicMock(return_value=8500)),
        ]
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/kb/3001/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["document_count"] == 5
        assert data["chunk_count"] == 120
        assert data["total_tokens"] == 8500

    @pytest.mark.asyncio
    async def test_empty_kb_zeros(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = _kb()
        db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=None)),
        ]
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/kb/3001/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_cross_tenant_404(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = _kb(tenant_id=9999)
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/kb/3001/stats")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_kb_not_found(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = None
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/kb/99999/stats")
        assert r.status_code == 404


class TestKBUpdate:
    @pytest.mark.asyncio
    async def test_update_name(self):
        app = _make_app()
        kb = _kb()
        db = AsyncMock()
        db.get.return_value = kb
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.put("/api/v1/kb/3001", json={"name": "新名称", "description": "新描述"})
        assert r.status_code == 200
        assert kb.name == "新名称"
        assert kb.description == "新描述"
