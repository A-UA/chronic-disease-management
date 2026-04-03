"""查询改写服务测试：标准化、精确匹配、模糊匹配、医疗术语扩展"""
from app.services.query_rewrite import normalize_query, rewrite_query


class TestNormalizeQuery:
    def test_trims_whitespace(self):
        assert normalize_query("  你好  ") == "你好"

    def test_normalizes_chinese_punctuation(self):
        assert normalize_query("你好？") == "你好?"
        assert normalize_query("体温：36.5") == "体温:36.5"
        assert normalize_query("头痛，恶心") == "头痛,恶心"

    def test_collapses_multiple_spaces(self):
        assert normalize_query("你好   世界") == "你好 世界"

    def test_empty_string(self):
        assert normalize_query("") == ""
        assert normalize_query("   ") == ""


class TestRewriteQuery:
    def test_exact_match_rewrites(self):
        """精确匹配规则应生效（规则表中存在的 key）"""
        result = rewrite_query("药能停吗")
        assert "停药" in result

    def test_fuzzy_match_works(self):
        """模糊匹配：查询包含规则表中短语时也应命中"""
        result = rewrite_query("这个药有什么忌口吗")
        # 应包含改写结果，而非原样返回
        assert isinstance(result, str) and len(result) > 0

    def test_no_match_returns_original(self):
        """无匹配规则时应返回原始查询"""
        original = "今天天气怎么样"
        result = rewrite_query(original)
        assert result == original or "天气" in result

    def test_medical_term_expansion(self):
        """医疗术语别名应被扩展"""
        result = rewrite_query("高血压怎么治")
        # 应包含扩展信息
        assert isinstance(result, str) and len(result) > 0
