from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.graph import END, StateGraph

from app.graph.security import SecurityContext
from app.graph.skills.base import skill_registry
from app.graph.state import AgentState
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


def _get_context(config: dict[str, Any] | None) -> SecurityContext:
    configurable = (config or {}).get("configurable", {})
    ctx = configurable.get("context") or (config or {}).get("context")
    if ctx is None:
        raise RuntimeError("Agent graph requires SecurityContext in config")
    return ctx


async def assistant_node(
    state: AgentState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = _get_context(config)
    llm = PluginRegistry.get("llm")

    # Check iterations
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return {"final_answer": "已达到最大推理论次，请重新提问。"}

    # Retrieve allowed skills and build tools
    available_skills = skill_registry.get_available(ctx.permissions)

    if available_skills:
        # Generate OpenAI compliant tool schemas from our SkillRegistry
        tool_schemas = [skill.to_openai_tool_schema() for skill in available_skills]
        llm_with_tools = llm.bind_tools(tool_schemas)
    else:
        llm_with_tools = llm

    system_message = {"role": "system", "content": "你是慢病管理的 AI 助手，请尽力运用工具查询健康数据与患者信息来回答问题。尽可能综合各种数据推导出患者的健康状况。必须用中文回答。"}

    messages = [system_message] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    # Check if final message
    final_answer = ""
    if not hasattr(response, "tool_calls") or not response.tool_calls:
        final_answer = response.content

    # Return message updates
    return {"messages": [response], "iteration": state.get("iteration", 0) + 1, "final_answer": final_answer}


async def tool_runner_node(
    state: AgentState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = _get_context(config)
    last_message = state["messages"][-1]

    tool_messages = []

    if hasattr(last_message, "tool_calls"):
        for tool_call in last_message.tool_calls:
            skill_name = tool_call["name"]
            skill_args = tool_call["args"]

            result = await skill_registry.execute(skill_name, ctx, skill_args)
            if result.success:
                content = result.to_context_string()
            else:
                content = f"执行失败: {result.error}"

            tool_messages.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))

    return {"messages": tool_messages}


def should_continue(state: AgentState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "end"
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("assistant", assistant_node)
    graph.add_node("tools", tool_runner_node)

    graph.set_entry_point("assistant")

    graph.add_conditional_edges(
        "assistant",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )

    graph.add_edge("tools", "assistant")

    return graph
