"""P0-2: 对话生命周期管理测试

测试目标：
1. 列出当前用户的对话
2. 获取对话详情（含消息历史）
3. 重命名对话
4. 删除对话
5. 跨用户隔离
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.deps import get_current_user, get_current_org, get_db


# ─── 模拟数据 ────────────────────────────────────────────────

def _dummy_user(uid=1001):
    user = MagicMock()
    user.id = uid
    return user


def _dummy_conversation(conv_id=5001, user_id=1001, org_id=2001, title="测试对话"):
    conv = MagicMock()
    conv.id = conv_id
    conv.user_id = user_id
    conv.org_id = org_id
    conv.kb_id = 3001
    conv.title = title
    conv.created_at = "2026-04-01T00:00:00"
    return conv


def _dummy_message(msg_id=6001, conv_id=5001, role="user", content="你好"):
    msg = MagicMock()
    msg.id = msg_id
    msg.conversation_id = conv_id
    msg.role = role
    msg.content = content
    msg.created_at = "2026-04-01T00:00:01"
    return msg


# ─── 辅助函数 ────────────────────────────────────────────────

def _make_app():
    """延迟导入，避免模块不存在时整个测试文件报 ImportError"""
    from app.api.endpoints.conversations import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/conversations")
    return app


class DummyScalarResult:
    def __init__(self, items=None, one=None):
        self._items = items or []
        self._one = one

    def scalars(self):
        mock = MagicMock()
        mock.all.return_value = self._items
        return mock

    def scalar_one_or_none(self):
        return self._one


# ─── 测试 ────────────────────────────────────────────────────

class TestListConversations:
    @pytest.mark.asyncio
    async def test_returns_user_conversations(self):
        """应返回当前用户的对话列表"""
        app = _make_app()
        user = _dummy_user()
        convs = [_dummy_conversation(5001), _dummy_conversation(5002, title="第二个对话")]
        db = AsyncMock()
        db.execute.return_value = DummyScalarResult(items=convs)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/conversations/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_empty_list(self):
        """无对话时应返回空列表"""
        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = DummyScalarResult(items=[])

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/conversations/")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetConversationDetail:
    @pytest.mark.asyncio
    async def test_returns_conversation_with_messages(self):
        """应返回对话详情，包含消息列表"""
        app = _make_app()
        conv = _dummy_conversation()
        msgs = [_dummy_message(role="user", content="你好"),
                _dummy_message(msg_id=6002, role="assistant", content="你好！")]
        db = AsyncMock()
        db.get.return_value = conv
        db.execute.return_value = DummyScalarResult(items=msgs)

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/conversations/5001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 5001
        assert len(data["messages"]) == 2

    @pytest.mark.asyncio
    async def test_404_for_nonexistent(self):
        """不存在的对话应返回 404"""
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = None

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/conversations/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_403_for_other_user(self):
        """不能查看其他用户的对话"""
        app = _make_app()
        conv = _dummy_conversation(user_id=9999)  # 属于另一个用户
        db = AsyncMock()
        db.get.return_value = conv

        app.dependency_overrides[get_current_user] = lambda: _dummy_user(uid=1001)
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/conversations/5001")
        assert resp.status_code == 403


class TestRenameConversation:
    @pytest.mark.asyncio
    async def test_rename_success(self):
        """应成功重命名对话"""
        app = _make_app()
        conv = _dummy_conversation()
        db = AsyncMock()
        db.get.return_value = conv

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch("/api/v1/conversations/5001",
                                  json={"title": "新标题"})
        assert resp.status_code == 200
        assert conv.title == "新标题"


class TestDeleteConversation:
    @pytest.mark.asyncio
    async def test_delete_success(self):
        """应成功删除对话"""
        app = _make_app()
        conv = _dummy_conversation()
        db = AsyncMock()
        db.get.return_value = conv

        app.dependency_overrides[get_current_user] = lambda: _dummy_user()
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/conversations/5001")
        assert resp.status_code == 200
        db.delete.assert_called_once_with(conv)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_delete_other_user_forbidden(self):
        """不能删除其他用户的对话"""
        app = _make_app()
        conv = _dummy_conversation(user_id=9999)
        db = AsyncMock()
        db.get.return_value = conv

        app.dependency_overrides[get_current_user] = lambda: _dummy_user(uid=1001)
        app.dependency_overrides[get_current_org] = lambda: 2001
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/conversations/5001")
        assert resp.status_code == 403
