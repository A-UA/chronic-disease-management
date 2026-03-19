import json
import hashlib
from typing import TypedDict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Chunk
from app.services.quota import redis_client

class Citation(TypedDict):
    doc_id: str
    ref: str
    page: int

# Mock embedding for now
class MockEmbeddings:
    def embed_query(self, text: str) -> list[float]:
        return [0.1] * 1536

embeddings_model = MockEmbeddings()

async def retrieve_chunks(db: AsyncSession, query: str, kb_id: UUID, org_id: UUID, limit: int = 5) -> list[Chunk]:
    # 1. Try Cache (Exact query match for now)
    query_hash = hashlib.sha256(query.strip().lower().encode()).hexdigest()
    cache_key = f"rag_cache:{org_id}:{kb_id}:{query_hash}"
    
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        # Note: We return raw data or reconstruct objects. 
        # For simplicity in this mock-heavy stage, we just log and continue to DB 
        # but in a real app we'd return deserialized chunks.
        # Let's implement actual retrieval from cache if it exists.
        try:
            chunk_ids = json.loads(cached_data)
            stmt = select(Chunk).where(Chunk.id.in_([UUID(cid) for cid in chunk_ids]))
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception:
            pass # Fallback to DB on cache error

    # 2. Vector Search using pgvector cosine distance
    query_embedding = embeddings_model.embed_query(query)
    
    # Explicit filtering by org_id and kb_id
    stmt = (
        select(Chunk)
        .where(Chunk.org_id == org_id, Chunk.kb_id == kb_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    chunks = list(result.scalars().all())
    
    # 3. Update Cache (TTL 1 hour)
    if chunks:
        await redis_client.setex(
            cache_key, 
            3600, 
            json.dumps([str(c.id) for c in chunks])
        )
    
    return chunks

def build_rag_prompt(query: str, chunks: list[Chunk], patient_name: str | None = None) -> tuple[str, list[dict[str, Citation]]]:
    context_blocks = []
    citations = []
    
    # Simple PII scrubbing: replace patient name in chunks if provided
    for i, chunk in enumerate(chunks):
        content = chunk.content
        if patient_name:
            content = content.replace(patient_name, "[PATIENT]")
            
        doc_ref = f"Doc {i+1}"
        context_blocks.append(f"[{doc_ref}]: {content}")
        citations.append({
            "doc_id": str(chunk.document_id),
            "ref": doc_ref,
            "page": chunk.page_number
        })
        
    context_str = "\n\n".join(context_blocks)
    
    # Anonymize query as well
    if patient_name:
        query = query.replace(patient_name, "[PATIENT]")
    
    prompt = (
        "You are a helpful AI assistant. Answer the user's question based strictly on the following context. "
        "The context belongs to a patient (referred to as [PATIENT]).\n"
        "If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context_str}\n\n"
        f"Question: {query}"
    )
    
    return prompt, citations
