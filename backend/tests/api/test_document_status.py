"""P1-3: 文档处理状态查询测试

测试目标：
1. 已完成文档返回 status=completed
2. 处理中文档返回 status=pending
3. 失败文档返回 status=failed + failed_reason
4. 文档不存在返回 404
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.deps import get_current_user, get_current_org, get_db
from app.api.endpoints.documents import router

app = FastAPI()
app.include_router(router, prefix="/api/v1")


def _dummy_user():
    u = MagicMock()
    u.id = 1001
    return u


def _dummy_doc(status="completed", failed_reason=None, org_id=2001):
    doc = MagicMock()
    doc.id = 4001
    doc.kb_id = 3001
    doc.org_id = org_id
    doc.file_name = "test.pdf"
    doc.status = status
    doc.failed_reason = failed_reason
    return doc


class TestDocumentStatus:
    @pytest.mark.asyncio
    async def test_completed_status(self):
        """已完成文档应返回 status=completed"""
        doc = _dummy_doc(status="completed")
        db = AsyncMock()
        db.get.return_value = doc

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/4001/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["failed_reason"] is None

    @pytest.mark.asyncio
    async def test_pending_status(self):
        """处理中文档应返回 status=pending"""
        doc = _dummy_doc(status="pending")
        db = AsyncMock()
        db.get.return_value = doc

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/4001/status")

        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_failed_status_with_reason(self):
        """失败文档应返回 failed_reason"""
        doc = _dummy_doc(status="failed", failed_reason="Embedding API error")
        db = AsyncMock()
        db.get.return_value = doc

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/4001/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert "Embedding" in data["failed_reason"]

    @pytest.mark.asyncio
    async def test_document_not_found(self):
        """不存在的文档应返回 404"""
        db = AsyncMock()
        db.get.return_value = None

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/99999/status")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_org_forbidden(self):
        """不能查看其他组织的文档状态"""
        doc = _dummy_doc(org_id=9999)  # 属于另一个组织
        db = AsyncMock()
        db.get.return_value = doc

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/4001/status")

        assert resp.status_code == 404
