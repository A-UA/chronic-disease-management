"""Agent 对话记忆测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.modules.agent.security import SecurityContext
from app.modules.agent.memory import prepare_query_with_memory


def _ctx():
    db = MagicMock()
    return SecurityContext(tenant_id=1, org_id=2, user_id=3, db=db)


class TestPrepareQueryWithMemory:
    @pytest.mark.asyncio
    async def test_no_conversation_returns_original(self):
        query, history = await prepare_query_with_memory(_ctx(), "测试", None)
        assert query == "测试"
        assert history == []

    @pytest.mark.asyncio
    async def test_zero_conversation_returns_original(self):
        query, history = await prepare_query_with_memory(_ctx(), "测试", 0)
        assert query == "测试"
        assert history == []

    @pytest.mark.asyncio
    async def test_empty_history_returns_original(self):
        ctx = _ctx()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        ctx = SecurityContext(
            tenant_id=1, org_id=2, user_id=3,
            db=MagicMock(execute=AsyncMock(return_value=mock_result)),
        )
        query, history = await prepare_query_with_memory(ctx, "测试查询", 123)
        assert query == "测试查询"
        assert history == []
