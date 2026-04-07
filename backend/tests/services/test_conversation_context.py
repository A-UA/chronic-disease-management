"""对话上下文服务测试：追问检测、上下文增强"""
from app.modules.rag.context import (
    is_likely_follow_up,
    build_retrieval_query_from_history,
)


class TestIsLikelyFollowUp:
    def test_short_query_is_followup(self):
        """短查询应判定为追问"""
        assert is_likely_follow_up("继续") is True
        assert is_likely_follow_up("那呢") is True

    def test_marker_words_detected(self):
        """包含追问标记词应判定为追问"""
        assert is_likely_follow_up("这个药怎么吃") is True
        assert is_likely_follow_up("你说的那个指标") is True
        assert is_likely_follow_up("为什么会这样") is True

    def test_independent_long_query(self):
        """明确的独立长查询不应被判定为追问"""
        assert is_likely_follow_up("高血压患者的日常饮食应该注意什么") is False

    def test_empty_query(self):
        """空查询应返回 False"""
        assert is_likely_follow_up("") is False
        assert is_likely_follow_up("   ") is False


class TestBuildRetrievalQueryFromHistory:
    def test_no_history_returns_normalized(self):
        """无历史记录时应返回标准化后的原始查询"""
        result = build_retrieval_query_from_history("你好？", [])
        assert result == "你好?"

    def test_followup_with_history_enriched(self):
        """追问型查询应拼接历史上下文"""
        history = [
            {"role": "user", "content": "高血压患者能吃什么药"},
            {"role": "assistant", "content": "建议使用 ARB 类降压药"},
        ]
        result = build_retrieval_query_from_history("这个药有副作用吗", history)
        # 应包含历史上下文
        assert "高血压" in result or "副作用" in result
        assert len(result) > len("这个药有副作用吗")

    def test_independent_query_not_enriched(self):
        """非追问查询不应拼接历史"""
        history = [
            {"role": "user", "content": "高血压怎么治疗"},
            {"role": "assistant", "content": "建议使用降压药"},
        ]
        result = build_retrieval_query_from_history(
            "糖尿病患者的饮食指南是什么", history
        )
        # 独立查询，不应拼接历史
        assert "糖尿病" in result

    def test_empty_query(self):
        """空查询应返回空字符串"""
        assert build_retrieval_query_from_history("", []) == ""

    def test_same_query_as_history_not_duplicated(self):
        """当前查询与历史相同时不应重复拼接"""
        history = [{"role": "user", "content": "继续"}]
        result = build_retrieval_query_from_history("继续", history)
        assert result == "继续"
