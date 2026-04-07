"""文档处理状态查询测试

覆盖：completed / pending / failed / 404 / 跨租户隔离
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import override_deps, TENANT_ID


def _make_app():
    from app.modules.rag.router_documents import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


def _doc(status="completed", failed_reason=None, tenant_id=TENANT_ID):
    d = MagicMock()
    d.id = 4001
    d.kb_id = 3001
    d.tenant_id = tenant_id
    d.org_id = 2001
    d.file_name = "test.pdf"
    d.status = status
    d.failed_reason = failed_reason
    return d


class TestDocumentStatus:
    @pytest.mark.asyncio
    async def test_completed(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = _doc("completed")
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/4001/status")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_pending(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = _doc("pending")
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/4001/status")
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_failed_with_reason(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = _doc("failed", "Embedding API error")
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/4001/status")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "failed"
        assert "Embedding" in data["failed_reason"]

    @pytest.mark.asyncio
    async def test_not_found(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = None
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/99999/status")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_tenant_404(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = _doc(tenant_id=9999)
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/4001/status")
        assert r.status_code == 404
