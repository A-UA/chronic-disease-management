"""对话生命周期管理测试

覆盖：列表、详情、重命名、删除、跨用户隔离
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import override_deps, MockScalarResult, TENANT_ID, ORG_ID, USER_ID


def _make_app():
    from app.modules.rag.router_conversations import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/conversations")
    return app


def _conv(conv_id=5001, user_id=USER_ID, tenant_id=TENANT_ID):
    c = MagicMock()
    c.id = conv_id
    c.user_id = user_id
    c.tenant_id = tenant_id
    c.kb_id = 3001
    c.title = "测试对话"
    c.created_at = "2026-04-01T00:00:00"
    return c


def _msg(msg_id=6001, role="user", content="你好"):
    m = MagicMock()
    m.id = msg_id
    m.conversation_id = 5001
    m.role = role
    m.content = content
    m.created_at = "2026-04-01T00:00:01"
    return m


class TestListConversations:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[_conv(), _conv(5002)])
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/conversations")
        assert r.status_code == 200
        assert len(r.json()) == 2

    @pytest.mark.asyncio
    async def test_empty_list(self):
        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[])
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/conversations")
        assert r.status_code == 200
        assert r.json() == []


class TestGetConversationDetail:
    @pytest.mark.asyncio
    async def test_returns_detail(self):
        app = _make_app()
        conv = _conv()
        msgs = [_msg(), _msg(6002, "assistant", "你好！")]
        db = AsyncMock()
        db.get.return_value = conv
        db.execute.return_value = MockScalarResult(items=msgs)
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/conversations/5001")
        assert r.status_code == 200
        assert r.json()["id"] == 5001

    @pytest.mark.asyncio
    async def test_404_not_found(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = None
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/conversations/99999")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_403_other_user(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = _conv(user_id=9999)  # 属于别人
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/conversations/5001")
        assert r.status_code == 403


class TestRenameConversation:
    @pytest.mark.asyncio
    async def test_rename_ok(self):
        app = _make_app()
        conv = _conv()
        db = AsyncMock()
        db.get.return_value = conv
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.patch("/api/v1/conversations/5001", json={"title": "新标题"})
        assert r.status_code == 200
        assert conv.title == "新标题"


class TestDeleteConversation:
    @pytest.mark.asyncio
    async def test_delete_ok(self):
        app = _make_app()
        conv = _conv()
        db = AsyncMock()
        db.get.return_value = conv
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.delete("/api/v1/conversations/5001")
        assert r.status_code == 200
        db.delete.assert_called_once_with(conv)

    @pytest.mark.asyncio
    async def test_delete_other_user_403(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = _conv(user_id=9999)
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.delete("/api/v1/conversations/5001")
        assert r.status_code == 403
