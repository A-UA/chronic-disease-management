"""SSE 流式聊天端点测试

覆盖：
1. 必须有知识库
2. 知识库不存在 → 404
3. 知识库跨租户 → 403
4. 聊天 SSE 流正常返回事件
"""
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import (
    override_deps, MockScalarResult, PatchRBAC, make_user,
    TENANT_ID, ORG_ID, USER_ID,
)


def _make_app():
    from app.modules.rag.router_chat import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/chat")
    return app


def _override_with_quota(app, db):
    """覆盖依赖并跳过配额检查"""
    from app.api.deps import verify_quota
    override_deps(app, db=db)
    app.dependency_overrides[verify_quota] = lambda: None


class TestChatKBNotFound:
    @pytest.mark.asyncio
    async def test_kb_not_found_404(self):
        """知识库不存在时应返回 404"""
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = None
        _override_with_quota(app, db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.post("/api/v1/chat", json={
                    "kb_id": 9999,
                    "conversation_id": 1001,
                    "query": "你好",
                })
        assert r.status_code == 404


class TestChatKBWrongTenant:
    @pytest.mark.asyncio
    async def test_kb_wrong_tenant_403(self):
        """知识库属于其他租户时应返回 403"""
        app = _make_app()
        kb = MagicMock()
        kb.id = 5001
        kb.tenant_id = 99999  # 不同租户

        db = AsyncMock()
        db.get.return_value = kb
        _override_with_quota(app, db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.post("/api/v1/chat", json={
                    "kb_id": 5001,
                    "conversation_id": 1001,
                    "query": "测试",
                })
        assert r.status_code == 403


class TestChatSSEStream:
    @pytest.mark.asyncio
    @patch("app.modules.rag.router_chat.registry")
    @patch("app.modules.rag.router_chat.retrieve_chunks", new_callable=AsyncMock)
    @patch("app.modules.rag.router_chat.build_rag_prompt")
    @patch("app.modules.rag.router_chat.build_retrieval_query_from_history")
    async def test_sse_stream_events(
        self, mock_context, mock_build_prompt, mock_retrieve, mock_registry
    ):
        """完整 SSE 流应返回 meta + chunk + done 事件"""
        app = _make_app()

        # 准备 KB
        kb = MagicMock()
        kb.id = 5001
        kb.tenant_id = TENANT_ID

        # 准备对话
        conv = MagicMock()
        conv.id = 1001
        conv.tenant_id = TENANT_ID
        conv.user_id = USER_ID
        conv.kb_id = 5001

        db = AsyncMock()
        # 第一次 get → KB，第二次 get → Conversation
        db.get.side_effect = [kb, conv]
        db.execute.return_value = MockScalarResult(items=[])  # 空历史
        _override_with_quota(app, db)

        # Mock 服务层
        mock_context.return_value = "测试问题"
        mock_retrieve.return_value = []
        mock_build_prompt.return_value = ("你是助手", [])

        # LLM provider
        async def fake_stream(prompt):
            yield "你好"
            yield "世界"

        llm = MagicMock()
        llm.model_name = "test-model"
        llm.stream_text = fake_stream
        mock_registry.get_llm.return_value = llm

        # Mock 独立会话（在 generate() 内部 from app.db.session import）
        mock_db_gen = AsyncMock()
        mock_db_gen.execute = AsyncMock()
        mock_db_gen.add = MagicMock()
        mock_db_gen.commit = AsyncMock()

        with PatchRBAC(), \
             patch("app.db.session.AsyncSessionLocal") as mock_session, \
             patch("app.modules.rag.router_chat.count_tokens", return_value=10), \
             patch("app.modules.rag.router_chat.check_quota_during_stream", new_callable=AsyncMock, return_value=True), \
             patch("app.modules.rag.router_chat.update_tenant_quota", new_callable=AsyncMock), \
             patch("app.modules.rag.router_chat.extract_statement_citations_structured", new_callable=AsyncMock, return_value=[]):
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db_gen)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.post("/api/v1/chat", json={
                    "kb_id": 5001,
                    "conversation_id": 1001,
                    "query": "你好吗",
                })

        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]

        # 解析 SSE 事件
        events = []
        for line in r.text.split("\n"):
            if line.startswith("event: "):
                events.append(line.replace("event: ", ""))

        assert "meta" in events, f"应包含 meta 事件，实际: {events}"
        assert "done" in events, f"应包含 done 事件，实际: {events}"
