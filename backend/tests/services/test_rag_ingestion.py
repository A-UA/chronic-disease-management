"""RAG 入库测试：切块、异步 embedding、文档状态管理"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rag_ingestion import (
    split_document_text,
    count_tokens,
    process_document,
    ChunkWithMeta,
)


# ── 切块测试 ──

def test_split_medical_headings():
    text = "主诉:\n反复头晕三天\n\n现病史:\n今晨加重"
    chunks = split_document_text(text)
    assert len(chunks) == 2
    assert all(isinstance(c, ChunkWithMeta) for c in chunks)
    assert "主诉" in chunks[0].content and "反复头晕三天" in chunks[0].content
    assert "现病史" in chunks[1].content and "今晨加重" in chunks[1].content


def test_split_extended_headings():
    """测试扩展后的医疗标题词典"""
    text = "手术记录:\n腹腔镜胆囊切除\n\n术中所见:\n胆囊壁增厚"
    chunks = split_document_text(text)
    assert len(chunks) == 2
    assert "手术记录" in chunks[0].content
    assert "术中所见" in chunks[1].content


def test_split_long_text_produces_multiple_chunks():
    sentence = "这是一个测试句子。"
    text = sentence * 200
    chunks = split_document_text(text, chunk_size=500, chunk_overlap=100)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.content) > 0


def test_split_empty_text():
    assert split_document_text("") == []
    assert split_document_text("   ") == []


def test_split_preserves_page_number():
    pages = ["第一页内容。", "第二页有更多内容。"]
    text = "\n\n".join(pages)
    chunks = split_document_text(text, pages=pages)
    assert len(chunks) >= 1
    assert chunks[0].page_number is not None


def test_chunk_meta_has_section_title():
    text = "主诉:\n头痛三天"
    chunks = split_document_text(text)
    assert chunks[0].section_title == "主诉"


# ── Token 计算测试 ──

def test_count_tokens_basic():
    t = count_tokens("hello world")
    assert isinstance(t, int) and t > 0


def test_count_tokens_chinese():
    t = count_tokens("你好世界")
    assert t > 0


# ── process_document 测试 ──

def _mock_doc():
    doc = MagicMock()
    doc.id = uuid4()
    doc.kb_id = uuid4()
    doc.org_id = uuid4()
    doc.uploader_id = uuid4()
    doc.status = "pending"
    doc.failed_reason = None
    doc.file_name = "test.txt"
    return doc


@pytest.mark.asyncio
async def test_process_document_completed():
    doc = _mock_doc()
    db = AsyncMock()
    db.get.return_value = doc
    db.add = MagicMock()

    provider = MagicMock()
    provider.embed_documents = AsyncMock(return_value=[[0.1] * 3])
    provider.model_name = "test"

    with patch("app.services.rag_ingestion.AsyncSessionLocal") as sf, \
         patch("app.services.rag_ingestion.registry.get_embedding", return_value=provider):
        sf.return_value.__aenter__.return_value = db
        await process_document(doc.id, "诊断:\n稳定样本")

    assert doc.status == "completed"
    assert doc.failed_reason is None
    assert db.commit.called


@pytest.mark.asyncio
async def test_process_document_failed():
    doc = _mock_doc()
    db = AsyncMock()
    db.get.return_value = doc
    db.add = MagicMock()

    provider = MagicMock()
    provider.embed_documents = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("app.services.rag_ingestion.AsyncSessionLocal") as sf, \
         patch("app.services.rag_ingestion.registry.get_embedding", return_value=provider):
        sf.return_value.__aenter__.return_value = db
        await process_document(doc.id, "诊断:\n稳定样本")

    assert doc.status == "failed"
    assert "boom" in doc.failed_reason


@pytest.mark.asyncio
async def test_process_document_not_found():
    db = AsyncMock()
    db.get.return_value = None
    with patch("app.services.rag_ingestion.AsyncSessionLocal") as sf:
        sf.return_value.__aenter__.return_value = db
        await process_document(uuid4(), "text")
    assert not db.add.called


@pytest.mark.asyncio
async def test_process_document_clears_old_failed_reason():
    doc = _mock_doc()
    doc.failed_reason = "old error"
    db = AsyncMock()
    db.get.return_value = doc
    db.add = MagicMock()

    provider = MagicMock()
    provider.embed_documents = AsyncMock(return_value=[[0.1] * 3])

    with patch("app.services.rag_ingestion.AsyncSessionLocal") as sf, \
         patch("app.services.rag_ingestion.registry.get_embedding", return_value=provider):
        sf.return_value.__aenter__.return_value = db
        await process_document(doc.id, "诊断:\n稳定样本")

    assert doc.failed_reason is None
