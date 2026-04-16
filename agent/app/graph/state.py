"""LangGraph Agent 状态定义"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict):
    """Agent 状态 — LangGraph 图的共享状态

    Attributes:
        messages: 对话消息列表
        query: 当前用户查询
        kb_id: 知识库 ID
        skill_results: Skill 执行结果缓存
        citations: RAG 引用
        final_answer: 最终回答
        iteration: 当前迭代轮次（安全防护）
        max_iterations: 最大迭代次数（默认 3）
    """

    messages: list[dict[str, str]]
    query: str
    kb_id: int
    skill_results: list[dict[str, Any]]
    citations: list[dict]
    final_answer: str
    iteration: int
    max_iterations: int
