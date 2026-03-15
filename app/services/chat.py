from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Chunk

# Mock embedding for now
class MockEmbeddings:
    def embed_query(self, text: str) -> List[float]:
        return [0.1] * 1536

embeddings_model = MockEmbeddings()

async def retrieve_chunks(db: AsyncSession, query: str, kb_id: UUID, limit: int = 5) -> List[Chunk]:
    query_embedding = embeddings_model.embed_query(query)
    
    # Vector Search using pgvector cosine distance
    stmt = (
        select(Chunk)
        .where(Chunk.kb_id == kb_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    return list(result.scalars().all())

def build_rag_prompt(query: str, chunks: List[Chunk], history: List[Dict[str, str]] = None) -> str:
    context_blocks = []
    citations = []
    
    for i, chunk in enumerate(chunks):
        doc_ref = f"Doc {i+1}"
        context_blocks.append(f"[{doc_ref}]: {chunk.content}")
        citations.append({
            "doc_id": str(chunk.document_id),
            "ref": doc_ref,
            "page": chunk.page_number
        })
        
    context_str = "\n\n".join(context_blocks)
    
    prompt = (
        "You are a helpful AI assistant. Answer the user's question based strictly on the following context. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context_str}\n\n"
        f"Question: {query}"
    )
    
    return prompt, citations
