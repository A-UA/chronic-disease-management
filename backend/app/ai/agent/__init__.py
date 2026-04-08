"""Agent module public interface."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.ai.agent.security import SecurityContext
from app.ai.agent.skills.base import skill_registry

__all__ = ["SecurityContext", "skill_registry", "run_agent"]


@lru_cache(maxsize=1)
def _get_compiled_agent_graph():
    from app.ai.agent.graph import build_agent_graph

    return build_agent_graph().compile()


async def run_agent(
    ctx: SecurityContext,
    query: str,
    kb_id: int,
    conversation_id: int | None = None,
) -> dict[str, Any]:
    """Agent entry point."""
    from app.ai.agent.memory import prepare_query_with_memory
    from app.ai.agent.state import AgentState

    enhanced_query, history = await prepare_query_with_memory(
        ctx,
        query,
        conversation_id,
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
    compiled_graph = _get_compiled_agent_graph()
    final_state = await compiled_graph.ainvoke(state, config={"context": ctx})

    return {
        "answer": final_state.get("final_answer", ""),
        "citations": final_state.get("citations", []),
        "skill_results": final_state.get("skill_results", []),
    }
