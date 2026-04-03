"""聊天服务测试：RAG 提示词构建、查询扩展复杂度判断"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.chat import build_rag_prompt, expand_query


def _mock_chunk(content="测试内容", doc_id=1001, chunk_id=2001, page=1):
    """创建模拟 Chunk 对象"""
    chunk = MagicMock()
    chunk.content = content
    chunk.document_id = doc_id
    chunk.id = chunk_id
    chunk.page_number = page
    return chunk


class TestBuildRagPrompt:
    def test_returns_prompt_and_citations(self):
        """应返回 (prompt, citations) 元组"""
        chunks = [_mock_chunk("高血压诊断标准")]
        prompt, citations = build_rag_prompt("什么是高血压", chunks)
        assert isinstance(prompt, str)
        assert isinstance(citations, list)
        assert len(citations) == 1

    def test_chinese_prompt_by_default(self):
        """默认应使用中文提示词"""
        chunks = [_mock_chunk("测试")]
        prompt, _ = build_rag_prompt("测试问题", chunks)
        assert "临床推理助手" in prompt
        assert "参考资料" in prompt
        assert "回答规则" in prompt

    def test_english_prompt_when_specified(self):
        """language='en' 应使用英文提示词"""
        chunks = [_mock_chunk("test content")]
        prompt, _ = build_rag_prompt("test question", chunks, language="en")
        assert "Clinical Reasoning Assistant" in prompt
        assert "CONTEXT" in prompt

    def test_citation_structure(self):
        """引用应包含 doc_id, chunk_id, ref, page, snippet"""
        chunks = [_mock_chunk("内容", doc_id=100, chunk_id=200, page=3)]
        _, citations = build_rag_prompt("问题", chunks)
        c = citations[0]
        assert c["doc_id"] == "100"
        assert c["chunk_id"] == "200"
        assert c["ref"] == "Doc 1"
        assert c["page"] == 3

    def test_multiple_chunks_indexed(self):
        """多个 chunk 应按序编号"""
        chunks = [_mock_chunk(f"内容{i}") for i in range(3)]
        prompt, citations = build_rag_prompt("问题", chunks)
        assert len(citations) == 3
        assert citations[0]["ref"] == "Doc 1"
        assert citations[1]["ref"] == "Doc 2"
        assert citations[2]["ref"] == "Doc 3"
        assert "[Doc 1]" in prompt
        assert "[Doc 3]" in prompt

    def test_patient_name_masked(self):
        """患者姓名应被替换为 [PATIENT]"""
        chunks = [_mock_chunk("张三的血压偏高")]
        prompt, _ = build_rag_prompt("张三的情况", chunks, patient_name="张三")
        assert "张三" not in prompt
        assert "[PATIENT]" in prompt

    def test_empty_chunks(self):
        """空 chunk 列表应正常工作"""
        prompt, citations = build_rag_prompt("问题", [])
        assert isinstance(prompt, str)
        assert citations == []


class TestExpandQuery:
    @pytest.mark.asyncio
    async def test_short_query_skips_expansion(self):
        """短查询（<15 字符）应跳过 LLM 扩展"""
        llm = AsyncMock()
        result = await expand_query("血压多少", [], llm)
        assert result == ["血压多少"]
        llm.complete_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_statement_skips_expansion(self):
        """不含疑问词的陈述句应跳过扩展"""
        llm = AsyncMock()
        result = await expand_query("患者今天情况稳定", [], llm)
        assert result == ["患者今天情况稳定"]
        llm.complete_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_complex_query_triggers_expansion(self):
        """含疑问词的复杂查询应触发 LLM 扩展"""
        llm = MagicMock()
        llm.complete_text = AsyncMock(return_value="1. 高血压的治疗方案\n2. 降压药物选择\n3. 血压控制目标")
        result = await expand_query("高血压患者应该如何选择降压药物？", [], llm)
        assert len(result) >= 1
        llm.complete_text.assert_called_once()
