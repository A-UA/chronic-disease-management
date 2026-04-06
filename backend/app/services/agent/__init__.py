"""Agent 模块公共接口"""
from __future__ import annotations

from typing import Any

from app.services.agent.security import SecurityContext
from app.services.agent.skills.base import skill_registry

__all__ = ["SecurityContext", "skill_registry", "run_agent"]


async def run_agent(
    ctx: SecurityContext,
    query: str,
    kb_id: int,
    conversation_id: int | None = None,
) -> dict[str, Any]:
    """Agent 入口 — 集成 Memory + Router + Skill/RAG + Answer

    Returns:
        {"answer": str, "citations": list, "skill_results": list}
    """
    from app.services.agent.memory import prepare_query_with_memory
    from app.services.agent.graph import (
        router_node, rag_node, skill_node, direct_answer_node,
    )
    from app.services.agent.state import AgentState

    # 1. Memory 增强
    enhanced_query, history = await prepare_query_with_memory(
        ctx, query, conversation_id,
    )

    # 2. 构建初始状态
    state: AgentState = {
        "messages": history,
        "query": enhanced_query,
        "kb_id": kb_id,
        "skill_results": [],
        "citations": [],
        "final_answer": "",
        "iteration": 0,
        "max_iterations": 3,
    }

    # 3. Router — 决定走哪个节点
    router_result = await router_node(state, ctx)
    state.update(router_result)

    # 4. 根据路由结果执行对应节点
    next_node = state.pop("_next", "rag_node")

    if "final_answer" in router_result and router_result["final_answer"]:
        pass  # 已达到最大轮次，router 已写入 final_answer
    elif next_node == "skill_node":
        node_result = await skill_node(state, ctx)
        state.update(node_result)
    elif next_node == "direct_answer":
        node_result = await direct_answer_node(state, ctx)
        state.update(node_result)
    else:
        # 默认走 RAG
        node_result = await rag_node(state, ctx)
        state.update(node_result)

    return {
        "answer": state.get("final_answer", ""),
        "citations": state.get("citations", []),
        "skill_results": state.get("skill_results", []),
    }
