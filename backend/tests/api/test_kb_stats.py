"""P1-1: 知识库统计信息测试

测试目标：
1. 返回文档数、chunk 数、总 token 数
2. 空知识库返回全零统计
3. 跨组织隔离
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.deps import get_current_user, get_current_org, get_db
from app.api.endpoints.knowledge_bases import router


app = FastAPI()
app.include_router(router, prefix="/api/v1/kb")


def _dummy_user(uid=1001):
    u = MagicMock()
    u.id = uid
    return u


class TestKBStats:
    @pytest.mark.asyncio
    async def test_returns_stats(self):
        """应返回文档数、chunk 数、总 token 数"""
        kb = MagicMock()
        kb.id = 3001
        kb.org_id = 2001

        db = AsyncMock()
        db.get.return_value = kb
        # 模拟三次 execute 调用：doc_count, chunk_count, total_tokens
        db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=5)),    # 5 个文档
            MagicMock(scalar=MagicMock(return_value=120)),  # 120 个 chunk
            MagicMock(scalar=MagicMock(return_value=8500)), # 8500 个 token
        ]

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/kb/3001/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["document_count"] == 5
        assert data["chunk_count"] == 120
        assert data["total_tokens"] == 8500

    @pytest.mark.asyncio
    async def test_empty_kb_returns_zeros(self):
        """空知识库应返回全零"""
        kb = MagicMock()
        kb.id = 3001
        kb.org_id = 2001

        db = AsyncMock()
        db.get.return_value = kb
        db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=None)),
        ]

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/kb/3001/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["document_count"] == 0
        assert data["chunk_count"] == 0
        assert data["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_cross_org_forbidden(self):
        """不能查看其他组织的知识库统计"""
        kb = MagicMock()
        kb.id = 3001
        kb.org_id = 9999  # 不同组织

        db = AsyncMock()
        db.get.return_value = kb

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/kb/3001/stats")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_kb_not_found(self):
        """不存在的知识库应返回 404"""
        db = AsyncMock()
        db.get.return_value = None

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/kb/99999/stats")

        assert resp.status_code == 404
