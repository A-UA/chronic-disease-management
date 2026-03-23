from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.services import rag_ingestion as _rag_ingestion


split_document_text = _rag_ingestion.split_document_text


async def process_document(document_id: UUID, file_content: str, pages: list[str] | None = None):
    """兼容层：委托给 rag_ingestion 的实际实现"""
    _rag_ingestion.AsyncSessionLocal = AsyncSessionLocal
    return await _rag_ingestion.process_document(document_id, file_content, pages=pages)
