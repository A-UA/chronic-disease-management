"""RAG 入库服务测试：切块、Token 计算、文档处理"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.rag.ingestion_legacy import (
    split_document_text,
    count_tokens,
    process_document,
    ChunkWithMeta,
    _get_encoding,
)


# ── 切块测试 ──

class TestSplitDocumentText:
    def test_medical_headings_split(self):
        """应按医疗标题正则分割文档"""
        text = "主诉:\n反复头晕三天\n\n现病史:\n今晨加重"
        chunks = split_document_text(text)
        assert len(chunks) == 2
        assert all(isinstance(c, ChunkWithMeta) for c in chunks)
        assert "主诉" in chunks[0].content and "反复头晕三天" in chunks[0].content
        assert "现病史" in chunks[1].content and "今晨加重" in chunks[1].content

    def test_extended_medical_headings(self):
        """应支持扩展医疗标题词典（手术记录、术中所见等）"""
        text = "手术记录:\n腹腔镜胆囊切除\n\n术中所见:\n胆囊壁增厚"
        chunks = split_document_text(text)
        assert len(chunks) == 2
        assert "手术记录" in chunks[0].content
        assert "术中所见" in chunks[1].content

    def test_long_text_multiple_chunks(self):
        """长文本应被分割为多个 chunk"""
        sentence = "这是一个测试句子。"
        text = sentence * 200
        chunks = split_document_text(text, chunk_size=500, chunk_overlap=100)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c.content) > 0

    def test_empty_text(self):
        """空文本应返回空列表"""
        assert split_document_text("") == []
        assert split_document_text("   ") == []

    def test_preserves_page_number(self):
        """应保留页码信息"""
        pages = ["第一页内容。", "第二页有更多内容。"]
        text = "\n\n".join(pages)
        chunks = split_document_text(text, pages=pages)
        assert len(chunks) >= 1
        assert chunks[0].page_number is not None

    def test_chunk_meta_has_section_title(self):
        """切块元数据应包含章节标题"""
        text = "主诉:\n头痛三天"
        chunks = split_document_text(text)
        assert chunks[0].section_title == "主诉"

    def test_single_section(self):
        """单章节文档应返回一个 chunk"""
        text = "诊断:\n高血压 2 级"
        chunks = split_document_text(text)
        assert len(chunks) == 1
        assert "高血压" in chunks[0].content


# ── Token 计算测试 ──

class TestCountTokens:
    def test_basic_english(self):
        """英文 Token 计算应返回正整数"""
        t = count_tokens("hello world")
        assert isinstance(t, int) and t > 0

    def test_chinese(self):
        """中文 Token 计算应返回正整数"""
        t = count_tokens("你好世界")
        assert t > 0

    def test_empty_string(self):
        """空字符串应返回 0"""
        assert count_tokens("") == 0

    def test_uses_cached_encoding(self):
        """_get_encoding 应返回缓存的编码器实例"""
        enc1 = _get_encoding("gpt-4o")
        enc2 = _get_encoding("gpt-4o")
        assert enc1 is enc2  # 同一对象，证明缓存生效

    def test_fallback_encoding(self):
        """未知模型应回退到 cl100k_base"""
        enc = _get_encoding("non-existent-model-xyz")
        assert enc is not None
        assert count_tokens("test", "non-existent-model-xyz") > 0


# ── process_document 测试 ──

def _mock_doc(doc_id=1001, org_id=2001):
    """创建模拟 Document 对象（使用 int 类型 ID）"""
    doc = MagicMock()
    doc.id = doc_id
    doc.kb_id = 3001
    doc.org_id = org_id
    doc.uploader_id = 4001
    doc.patient_id = None
    doc.status = "pending"
    doc.failed_reason = None
    doc.file_name = "test.txt"
    return doc


class TestProcessDocument:
    @pytest.mark.asyncio
    async def test_completed_successfully(self):
        """文档处理成功后 status 应为 completed"""
        doc = _mock_doc()
        db = AsyncMock()
        db.get.return_value = doc
        db.add = MagicMock()

        provider = MagicMock()
        provider.embed_documents = AsyncMock(return_value=[[0.1] * 3])
        provider.model_name = "test"
        provider.get_dimension.return_value = 3

        with patch("app.modules.rag.ingestion_legacy.AsyncSessionLocal") as sf, \
             patch("app.modules.rag.ingestion_legacy.registry") as reg:
            sf.return_value.__aenter__ = AsyncMock(return_value=db)
            sf.return_value.__aexit__ = AsyncMock(return_value=False)
            reg.get_embedding.return_value = provider
            reg.get_llm.return_value = MagicMock()
            await process_document(doc.id, "诊断:\n稳定样本", org_id=doc.org_id)

        assert doc.status == "completed"
        assert doc.failed_reason is None
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_marks_failed_on_error(self):
        """embedding 失败时 status 应标记为 failed"""
        doc = _mock_doc()
        db = AsyncMock()
        db.get.return_value = doc
        db.add = MagicMock()

        provider = MagicMock()
        provider.embed_documents = AsyncMock(side_effect=RuntimeError("boom"))
        provider.model_name = "test"

        with patch("app.modules.rag.ingestion_legacy.AsyncSessionLocal") as sf, \
             patch("app.modules.rag.ingestion_legacy.registry") as reg:
            sf.return_value.__aenter__ = AsyncMock(return_value=db)
            sf.return_value.__aexit__ = AsyncMock(return_value=False)
            reg.get_embedding.return_value = provider
            reg.get_llm.return_value = MagicMock()
            await process_document(doc.id, "诊断:\n稳定样本", org_id=doc.org_id)

        assert doc.status == "failed"
        assert "boom" in doc.failed_reason

    @pytest.mark.asyncio
    async def test_not_found_no_crash(self):
        """文档不存在时应安全跳过"""
        db = AsyncMock()
        db.get.return_value = None

        with patch("app.modules.rag.ingestion_legacy.AsyncSessionLocal") as sf:
            sf.return_value.__aenter__ = AsyncMock(return_value=db)
            sf.return_value.__aexit__ = AsyncMock(return_value=False)
            await process_document(99999, "text", org_id=2001)

        assert not db.add.called

    @pytest.mark.asyncio
    async def test_clears_old_failed_reason(self):
        """重新入库成功后应清除旧的 failed_reason"""
        doc = _mock_doc()
        doc.failed_reason = "old error"
        db = AsyncMock()
        db.get.return_value = doc
        db.add = MagicMock()

        provider = MagicMock()
        provider.embed_documents = AsyncMock(return_value=[[0.1] * 3])
        provider.model_name = "test"
        provider.get_dimension.return_value = 3

        with patch("app.modules.rag.ingestion_legacy.AsyncSessionLocal") as sf, \
             patch("app.modules.rag.ingestion_legacy.registry") as reg:
            sf.return_value.__aenter__ = AsyncMock(return_value=db)
            sf.return_value.__aexit__ = AsyncMock(return_value=False)
            reg.get_embedding.return_value = provider
            reg.get_llm.return_value = MagicMock()
            await process_document(doc.id, "诊断:\n稳定样本", org_id=doc.org_id)

        assert doc.failed_reason is None

    @pytest.mark.asyncio
    async def test_persists_patient_id_in_chunk_metadata(self):
        """chunk 元数据中应包含 patient_id"""
        doc = _mock_doc()
        doc.patient_id = 5001
        db = AsyncMock()
        db.get.return_value = doc
        db.add = MagicMock()

        provider = MagicMock()
        provider.embed_documents = AsyncMock(return_value=[[0.1] * 3])
        provider.model_name = "test"
        provider.get_dimension.return_value = 3

        with patch("app.modules.rag.ingestion_legacy.AsyncSessionLocal") as sf, \
             patch("app.modules.rag.ingestion_legacy.registry") as reg:
            sf.return_value.__aenter__ = AsyncMock(return_value=db)
            sf.return_value.__aexit__ = AsyncMock(return_value=False)
            reg.get_embedding.return_value = provider
            reg.get_llm.return_value = MagicMock()
            await process_document(doc.id, "诊断:\n稳定样本", org_id=doc.org_id)

        chunk = db.add.call_args_list[0].args[0]
        assert chunk.metadata_["patient_id"] == str(doc.patient_id)
