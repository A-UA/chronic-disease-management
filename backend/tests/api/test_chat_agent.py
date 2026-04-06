"""Agent 集成测试 — run_agent 高层 API"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent.security import SecurityContext


def _make_ctx(perms=frozenset({"chat:use"})):
    return SecurityContext(
        tenant_id=1, org_id=2, user_id=3,
        permissions=perms, db=MagicMock(),
    )


class TestRunAgent:
    @pytest.mark.asyncio
    @patch("app.services.provider_registry.registry")
    async def test_direct_answer_when_no_skills_registered(self, mock_registry):
        """无 Skills 注册时，router 直接走 direct_answer（不调 LLM 路由）"""
        mock_llm = MagicMock()
        # router 不会调 LLM（因为无可用 skill），只有 direct_answer_node 调
        mock_llm.complete_text = AsyncMock(return_value="这是一个通用回答")
        mock_registry.get_llm.return_value = mock_llm

        # 用一个空的 registry 保证无 skills
        with patch("app.services.agent.graph.skill_registry") as empty_reg:
            empty_reg.get_available.return_value = []

            from app.services.agent import run_agent
            result = await run_agent(ctx=_make_ctx(), query="你好", kb_id=1)
            assert result["answer"] == "这是一个通用回答"
            assert result["citations"] == []

    @pytest.mark.asyncio
    @patch("app.services.provider_registry.registry")
    async def test_max_iterations_guard(self, mock_registry):
        """超过 max_iterations 应返回固定提示"""
        from app.services.agent.graph import router_node
        from app.services.agent.state import AgentState

        state: AgentState = {
            "messages": [], "query": "测试", "kb_id": 1,
            "skill_results": [], "citations": [],
            "final_answer": "", "iteration": 3, "max_iterations": 3,
        }
        result = await router_node(state, _make_ctx())
        assert "最大推理轮次" in result["final_answer"]

    @pytest.mark.asyncio
    @patch("app.services.provider_registry.registry")
    async def test_skill_call_for_bmi(self, mock_registry):
        """BMI 计算应走 skill_node 路径"""
        mock_llm = MagicMock()
        mock_llm.complete_text = AsyncMock(
            side_effect=[
                # router 选择 bmi_calculator
                '{"skill": "bmi_calculator", "params": {"height_cm": 170, "weight_kg": 65}}',
                # skill_node synthesis
                "根据计算，BMI 为 22.5，属于正常范围。",
            ]
        )
        mock_registry.get_llm.return_value = mock_llm

        # 确保 calculator_skills 已注册
        import app.services.agent.skills.calculator_skills  # noqa: F401

        from app.services.agent import run_agent
        result = await run_agent(ctx=_make_ctx(), query="身高170体重65的BMI是多少", kb_id=1)
        assert result["answer"]
        assert len(result["skill_results"]) > 0
        assert result["skill_results"][0]["skill"] == "bmi_calculator"
        assert result["skill_results"][0]["data"]["bmi"] == 22.5
