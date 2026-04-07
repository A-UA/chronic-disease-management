"""Agent module public interface"""
from __future__ import annotations

from typing import Any

from app.modules.agent.security import SecurityContext
from app.modules.agent.skills.base import skill_registry

__all__ = ["SecurityContext", "skill_registry", "run_agent"]


async def run_agent(
    ctx: SecurityContext,
    query: str,
    kb_id: int,
    conversation_id: int | None = None,
) -> dict[str, Any]:
    """Agent entry point"""
    from app.modules.agent.memory import prepare_query_with_memory
    from app.modules.agent.graph import (
        router_node, rag_node, skill_node, direct_answer_node,
    )
    from app.modules.agent.state import AgentState

    enhanced_query, history = await prepare_query_with_memory(
        ctx, query, conversation_id,
    )

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

    router_result = await router_node(state, ctx)
    state.update(router_result)

    next_node = state.pop("_next", "rag_node")

    if "final_answer" in router_result and router_result["final_answer"]:
        pass
    elif next_node == "skill_node":
        node_result = await skill_node(state, ctx)
        state.update(node_result)
    elif next_node == "direct_answer":
        node_result = await direct_answer_node(state, ctx)
        state.update(node_result)
    else:
        node_result = await rag_node(state, ctx)
        state.update(node_result)

    return {
        "answer": state.get("final_answer", ""),
        "citations": state.get("citations", []),
        "skill_results": state.get("skill_results", []),
    }
