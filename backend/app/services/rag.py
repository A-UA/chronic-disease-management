from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.services import rag_ingestion as _rag_ingestion


embeddings_model = _rag_ingestion.embeddings_model
split_document_text = _rag_ingestion.split_document_text


async def process_document(document_id: UUID, file_content: str):
    _rag_ingestion.AsyncSessionLocal = AsyncSessionLocal
    _rag_ingestion.embeddings_model = embeddings_model
    return await _rag_ingestion.process_document(document_id, file_content)
