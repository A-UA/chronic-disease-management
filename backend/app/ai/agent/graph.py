"""LangGraph 图定义 — 核心编排逻辑

图结构：
  START → router → [rag_node | skill_node | direct_answer] → END
                            ↑ skill 失败降级到 rag_node ↗
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.ai.agent.security import SecurityContext
from app.ai.agent.skills.base import skill_registry
from app.ai.agent.state import AgentState

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3


# ---------- 节点函数 ----------


async def router_node(state: AgentState, ctx: SecurityContext) -> dict[str, Any]:
    """意图路由：让 LLM 决定调用哪个 Skill"""
    if state["iteration"] >= state["max_iterations"]:
        return {"final_answer": "已达到最大推理轮次，请重新提问。"}

    available = skill_registry.get_available(ctx.permissions)
    if not available:
        return {"_next": "direct_answer"}

    tool_list = "\n".join(f"- {s.name}: {s.description}" for s in available)
    prompt = (
        f"你是慢病管理 AI 助手的意图路由器。\n"
        f"可用技能:\n{tool_list}\n\n"
        f"用户问题: {state['query']}\n\n"
        f"如需调用技能返回 JSON: {{\"skill\": \"名称\", \"params\": {{}}}}\n"
        f"如不需要返回: {{\"skill\": \"none\"}}\n"
        f"只返回 JSON，不要附加任何说明。"
    )

    from app.plugins.provider_compat import registry
    llm = registry.get_llm()
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
        logger.warning("Router 解析失败，降级到 RAG", exc_info=True)
        return {"_next": "rag_node"}


async def rag_node(state: AgentState, ctx: SecurityContext) -> dict[str, Any]:
    """RAG 检索节点 — 桥接现有 retrieve_chunks + build_rag_prompt"""
    from app.ai.rag.chat_service import build_rag_prompt, retrieve_chunks
    from app.plugins.provider_compat import registry

    llm = registry.get_llm()
    chunks = await retrieve_chunks(
        db=ctx.db, query=state["query"], kb_id=state["kb_id"],
        org_id=ctx.org_id, user_id=ctx.user_id, llm_provider=llm,
    )
    if not chunks:
        return {"final_answer": "未找到相关文档内容，无法回答此问题。", "citations": []}

    prompt, citations = build_rag_prompt(state["query"], chunks)
    response = await llm.complete_text(prompt)
    return {"final_answer": response, "citations": citations}


async def skill_node(state: AgentState, ctx: SecurityContext) -> dict[str, Any]:
    """技能执行节点"""
    skill_name = state.get("_skill_name", "")
    skill_params = state.get("_skill_params", {})
    result = await skill_registry.execute(skill_name, ctx, skill_params)

    if not result.success:
        # Skill 失败，降级到 RAG
        return await rag_node(state, ctx)

    # 用 Skill 结果构建 prompt 让 LLM 合成回答
    from app.plugins.provider_compat import registry
    llm = registry.get_llm()
    prompt = (
        f"你是慢病管理 AI 助手。以下是通过数据查询获得的信息：\n\n"
        f"{result.to_context_string()}\n\n"
        f"用户问题：{state['query']}\n\n"
        f"请基于以上数据用中文 Markdown 格式回答。"
    )
    response = await llm.complete_text(prompt)
    return {
        "final_answer": response,
        "skill_results": [
            {"skill": skill_name, "params": skill_params, "data": result.data},
        ],
    }


async def direct_answer_node(state: AgentState, ctx: SecurityContext) -> dict[str, Any]:
    """直接回答节点 — 无需 Skill，LLM 直接回答"""
    from app.plugins.provider_compat import registry
    llm = registry.get_llm()
    prompt = f"你是慢病管理 AI 助手。请用中文 Markdown 回答：\n\n{state['query']}"
    response = await llm.complete_text(prompt)
    return {"final_answer": response}


def build_agent_graph() -> StateGraph:
    """构建 Agent 图定义（编译前的蓝图）"""
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("skill_node", skill_node)
    graph.add_node("direct_answer", direct_answer_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        lambda s: s.get("_next", "rag_node"),
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
