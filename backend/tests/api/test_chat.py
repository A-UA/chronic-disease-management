"""Chat 模块测试

覆盖：标题生成工具函数
注意：SSE 流式端点需要完整的 RAG 管道 mock，放在集成测试中
"""
import pytest


class TestGenerateTitle:
    def test_short_query(self):
        from app.modules.rag.router_chat import _generate_title
        assert _generate_title("你好") == "你好"

    def test_truncate_long_query(self):
        from app.modules.rag.router_chat import _generate_title
        long = "这是一个非常长的查询" * 10
        result = _generate_title(long, max_len=20)
        assert len(result) <= 23  # 留余量给中文字符

    def test_sentence_boundary(self):
        from app.modules.rag.router_chat import _generate_title
        result = _generate_title("高血压怎么治疗？后续如何复查", max_len=50)
        assert "？" in result
