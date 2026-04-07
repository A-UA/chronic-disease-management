"""LangGraph Agent 图 + 状态测试"""
import pytest
from app.modules.agent.state import AgentState


class TestAgentState:
    def test_state_creation(self):
        state: AgentState = {
            "messages": [],
            "query": "测试",
            "kb_id": 1,
            "skill_results": [],
            "citations": [],
            "final_answer": "",
            "iteration": 0,
            "max_iterations": 3,
        }
        assert state["query"] == "测试"
        assert state["max_iterations"] == 3

    def test_iteration_guard(self):
        state: AgentState = {
            "messages": [],
            "query": "",
            "kb_id": 1,
            "skill_results": [],
            "citations": [],
            "final_answer": "",
            "iteration": 3,
            "max_iterations": 3,
        }
        assert state["iteration"] >= state["max_iterations"]


class TestBuildAgentGraph:
    def test_graph_builds_without_error(self):
        from app.modules.agent.graph import build_agent_graph
        graph = build_agent_graph()
        assert graph is not None
        # 验证节点已注册
        assert "router" in graph.nodes
        assert "rag_node" in graph.nodes
        assert "skill_node" in graph.nodes
        assert "direct_answer" in graph.nodes
