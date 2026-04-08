from __future__ import annotations

from types import SimpleNamespace


def test_estimate_tokens_chinese_has_minimum_of_one() -> None:
    from app.ai.rag.conversation import estimate_tokens_chinese

    assert estimate_tokens_chinese("") == 1
    assert estimate_tokens_chinese("糖") == 1


def test_load_history_by_token_budget_keeps_latest_messages_within_budget() -> None:
    from app.ai.rag.conversation import load_history_by_token_budget

    messages = [
        SimpleNamespace(role="user", content="a" * 30),
        SimpleNamespace(role="assistant", content="b" * 30),
        SimpleNamespace(role="user", content="c" * 3),
    ]

    history = load_history_by_token_budget(messages, max_tokens=25)

    assert history == [
        {"role": "assistant", "content": "b" * 30},
        {"role": "user", "content": "c" * 3},
    ]


def test_build_retrieval_query_from_history_is_reexported() -> None:
    from app.ai.rag.conversation import build_retrieval_query_from_history

    history = [{"role": "user", "content": "最近血糖偏高，需要控制饮食"}]
    query = build_retrieval_query_from_history("那现在情况呢？", history)

    assert "最近血糖偏高" in query
    assert "那现在情况呢" in query
