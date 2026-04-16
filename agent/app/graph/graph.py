from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.ai.agent.security import SecurityContext
from app.ai.agent.skills.base import skill_registry
from app.ai.agent.state import AgentState
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


def _get_context(config: dict[str, Any] | None) -> SecurityContext:
    configurable = (config or {}).get("configurable", {})
    ctx = configurable.get("context") or (config or {}).get("context")
    if ctx is None:
        raise RuntimeError("Agent graph requires SecurityContext in config")
    return ctx


async def router_node(
    state: AgentState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = _get_context(config)
    if state["iteration"] >= state["max_iterations"]:
        return {"final_answer": "已达到最大推理轮次，请重新提问。"}

    available = skill_registry.get_available(ctx.permissions)
    if not available:
        return {"_next": "direct_answer"}

    tool_list = "\n".join(f"- {skill.name}: {skill.description}" for skill in available)
    prompt = (
        "你是慢病管理 AI 助手的意图路由器。\n"
        f"可用技能:\n{tool_list}\n\n"
        f"用户问题: {state['query']}\n\n"
        '如需调用技能返回 JSON: {"skill": "名称", "params": {}}\n'
        '如不需要返回 {"skill": "none"}\n'
        "只返回 JSON，不要附加任何说明。"
    )

    llm = PluginRegistry.get("llm")
    try:
        response = await llm.complete_text(prompt)
        parsed = json.loads(response.strip())
        skill_name = parsed.get("skill", "none")
        if skill_name == "none":
            return {"_next": "direct_answer"}
        return {
            "_next": "skill_node",
            "_skill_name": skill_name,
            "_skill_params": parsed.get("params", {}),
        }
    except Exception:
        logger.warning("Agent router failed; falling back to RAG", exc_info=True)
        return {"_next": "rag_node"}


async def rag_node(
    state: AgentState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = _get_context(config)
    from app.ai.rag.prompt import build_rag_prompt
    from app.ai.rag.retrieval import retrieve_chunks

    llm = PluginRegistry.get("llm")
    chunks = await retrieve_chunks(
        db=ctx.db,
        query=state["query"],
        kb_id=state["kb_id"],
        org_id=ctx.org_id,
        user_id=ctx.user_id,
        llm_provider=llm,
    )
    if not chunks:
        return {
            "final_answer": "未找到相关文档内容，无法回答此问题。",
            "citations": [],
        }

    prompt, citations = build_rag_prompt(state["query"], chunks)
    response = await llm.complete_text(prompt)
    return {"final_answer": response, "citations": citations}


async def skill_node(
    state: AgentState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = _get_context(config)
    skill_name = state.get("_skill_name", "")
    skill_params = state.get("_skill_params", {})
    result = await skill_registry.execute(skill_name, ctx, skill_params)

    if not result.success:
        return await rag_node(state, config)

    llm = PluginRegistry.get("llm")
    prompt = (
        "你是慢病管理 AI 助手。以下是通过数据查询获得的信息：\n\n"
        f"{result.to_context_string()}\n\n"
        f"用户问题：{state['query']}\n\n"
        "请基于以上数据用中文 Markdown 格式回答。"
    )
    response = await llm.complete_text(prompt)
    return {
        "final_answer": response,
        "skill_results": [
            {"skill": skill_name, "params": skill_params, "data": result.data},
        ],
    }


async def direct_answer_node(
    state: AgentState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _get_context(config)
    llm = PluginRegistry.get("llm")
    prompt = f"你是慢病管理 AI 助手。请用中文 Markdown 回答：\n\n{state['query']}"
    response = await llm.complete_text(prompt)
    return {"final_answer": response}


def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("skill_node", skill_node)
    graph.add_node("direct_answer", direct_answer_node)
    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        lambda state: state.get("_next", "rag_node"),
        {
            "rag_node": "rag_node",
            "skill_node": "skill_node",
            "direct_answer": "direct_answer",
        },
    )
    graph.add_edge("rag_node", END)
    graph.add_edge("skill_node", END)
    graph.add_edge("direct_answer", END)
    return graph
