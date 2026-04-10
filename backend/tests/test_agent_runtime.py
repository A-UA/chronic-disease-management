from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_run_agent_executes_compiled_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.ai.agent import run_agent
    from app.ai.agent.security import SecurityContext

    calls: list[tuple[str, object]] = []

    async def fake_prepare_query_with_memory(ctx, query, conversation_id):
        calls.append(("prepare", conversation_id))
        return "enhanced-query", [{"role": "user", "content": "history"}]

    class FakeCompiledGraph:
        async def ainvoke(self, state, config=None):
            calls.append(("ainvoke", state.copy()))
            return {
                **state,
                "final_answer": "graph-answer",
                "citations": [{"ref": "Doc 1"}],
                "skill_results": [{"skill": "rag_search"}],
            }

    class FakeGraphBuilder:
        def compile(self):
            calls.append(("compile", None))
            return FakeCompiledGraph()

    monkeypatch.setattr(
        "app.ai.agent.memory.prepare_query_with_memory",
        fake_prepare_query_with_memory,
    )
    monkeypatch.setattr(
        "app.ai.agent.graph.build_agent_graph",
        lambda: FakeGraphBuilder(),
    )

    result = await run_agent(
        ctx=SecurityContext(
            tenant_id=1,
            org_id=2,
            user_id=3,
            roles=(),
            permissions=frozenset({"chat:use"}),
            db=SimpleNamespace(),
        ),
        query="原始问题",
        kb_id=10,
        conversation_id=20,
    )

    assert result == {
        "answer": "graph-answer",
        "citations": [{"ref": "Doc 1"}],
        "skill_results": [{"skill": "rag_search"}],
    }
    assert calls[0] == ("prepare", 20)
    assert calls[1] == ("compile", None)
    assert calls[2][0] == "ainvoke"
    assert calls[2][1]["query"] == "enhanced-query"
    assert calls[2][1]["messages"] == [{"role": "user", "content": "history"}]
