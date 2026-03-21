from app.services.conversation_context import build_retrieval_query_from_history


def test_build_retrieval_query_from_history_expands_follow_up_question():
    retrieval_query = build_retrieval_query_from_history(
        current_query="那这个药还要继续吃吗？",
        history_messages=[
            {"role": "user", "content": "2 型糖尿病患者空腹血糖高怎么办？"},
            {"role": "assistant", "content": "建议先复查空腹血糖并继续控制饮食。"},
        ],
    )

    assert "2 型糖尿病患者空腹血糖高怎么办" in retrieval_query
    assert "那这个药还要继续吃吗" in retrieval_query


def test_build_retrieval_query_from_history_keeps_standalone_question_unchanged():
    retrieval_query = build_retrieval_query_from_history(
        current_query="高血压患者应该如何监测血压？",
        history_messages=[
            {"role": "user", "content": "上一题"},
        ],
    )

    assert retrieval_query == "高血压患者应该如何监测血压?"
