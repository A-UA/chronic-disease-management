"""聊天端点辅助函数测试：标题生成、Token 估算、历史窗口"""
from unittest.mock import MagicMock
from app.api.endpoints.chat import (
    _generate_title,
    _estimate_tokens_chinese,
    _load_history_by_token_budget,
)


class TestGenerateTitle:
    def test_short_query_unchanged(self):
        """短查询应直接作为标题"""
        assert _generate_title("血压高吗") == "血压高吗"

    def test_truncated_at_sentence_boundary(self):
        """应在句号/问号处截断"""
        assert _generate_title("高血压怎么治？需要吃药吗") == "高血压怎么治？"

    def test_long_query_with_ellipsis(self):
        """超长查询应截断并添加省略号"""
        long_query = "这是一个非常长的查询" * 10
        result = _generate_title(long_query)
        assert len(result) <= 55  # 50 + '...'
        assert result.endswith("...")

    def test_exact_boundary(self):
        """刚好 50 字符的查询不应截断"""
        query = "a" * 50
        assert _generate_title(query) == query


class TestEstimateTokensChinese:
    def test_basic_estimation(self):
        """中文文本应按约 1.5 字/token 估算"""
        result = _estimate_tokens_chinese("你好世界测试文本")
        assert result > 0
        assert result == max(1, int(len("你好世界测试文本") / 1.5))

    def test_minimum_one_token(self):
        """至少返回 1"""
        assert _estimate_tokens_chinese("a") >= 1

    def test_empty_returns_one(self):
        """空字符串也至少返回 1"""
        assert _estimate_tokens_chinese("") >= 1


class TestLoadHistoryByTokenBudget:
    def _make_msgs(self, contents):
        """创建模拟 Message 对象列表"""
        msgs = []
        for role, content in contents:
            msg = MagicMock()
            msg.role = role
            msg.content = content
            msgs.append(msg)
        return msgs

    def test_within_budget(self):
        """预算内的消息应全部返回"""
        msgs = self._make_msgs([
            ("user", "你好"),
            ("assistant", "你好！"),
        ])
        result = _load_history_by_token_budget(msgs, max_tokens=2000)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_exceeds_budget_truncates(self):
        """超出预算应从最旧的开始截断"""
        msgs = self._make_msgs([
            ("user", "很久以前的消息" * 100),  # 很长
            ("assistant", "很久以前的回复" * 100),  # 很长
            ("user", "最近的问题"),  # 短
        ])
        result = _load_history_by_token_budget(msgs, max_tokens=50)
        # 应优先保留最近的消息
        assert len(result) < len(msgs)
        assert result[-1]["content"] == "最近的问题"

    def test_empty_history(self):
        """空历史应返回空列表"""
        result = _load_history_by_token_budget([], max_tokens=2000)
        assert result == []

    def test_preserves_order(self):
        """返回的消息应保持时间正序"""
        msgs = self._make_msgs([
            ("user", "第一条"),
            ("assistant", "第二条"),
            ("user", "第三条"),
        ])
        result = _load_history_by_token_budget(msgs, max_tokens=2000)
        assert result[0]["content"] == "第一条"
        assert result[-1]["content"] == "第三条"
