from app.services.query_rewrite import prepare_retrieval_query


def test_prepare_retrieval_query_normalizes_whitespace_and_full_width_punctuation():
    prepared = prepare_retrieval_query("  血糖高怎么办？\n\n  需要  复查吗？  ")

    assert prepared.original_query == "  血糖高怎么办？\n\n  需要  复查吗？  "
    assert prepared.normalized_query == "血糖高怎么办? 需要 复查吗?"
    assert prepared.retrieval_query == "血糖高怎么办? 需要 复查吗?"


def test_prepare_retrieval_query_rewrites_follow_up_style_prompts():
    prepared = prepare_retrieval_query("这个药还要继续吃吗")

    assert prepared.normalized_query == "这个药还要继续吃吗"
    assert prepared.retrieval_query == "用药是否需要继续"
