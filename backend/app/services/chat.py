import json
import hashlib
from typing import TypedDict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import Chunk
from app.services.quota import redis_client

class Citation(TypedDict):
    doc_id: str
    ref: str
    page: int | None

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
        try:
            chunk_ids = json.loads(cached_data)
            stmt = select(Chunk).where(Chunk.id.in_([UUID(cid) for cid in chunk_ids]))
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception:
            pass # Fallback to DB on cache error

    # 2. Vector Search (Semantic)
    query_embedding = embeddings_model.embed_query(query)
    vector_stmt = (
        select(Chunk)
        .where(Chunk.org_id == org_id, Chunk.kb_id == kb_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(limit * 2)
    )
    vector_res = await db.execute(vector_stmt)
    vector_chunks = list(vector_res.scalars().all())

    # 3. Keyword Search (BM25-like using TSVector)
    keyword_stmt = (
        select(Chunk)
        .where(
            Chunk.org_id == org_id, 
            Chunk.kb_id == kb_id,
            Chunk.tsv_content.op('@@')(func.plainto_tsquery('chinese', query))
        )
        .order_by(func.ts_rank(Chunk.tsv_content, func.plainto_tsquery('chinese', query)).desc())
        .limit(limit * 2)
    )
    keyword_res = await db.execute(keyword_stmt)
    keyword_chunks = list(keyword_res.scalars().all())

    # 4. Reciprocal Rank Fusion (RRF)
    k = 60
    scores = {}
    chunk_map = {}

    for rank, chunk in enumerate(vector_chunks):
        scores[chunk.id] = scores.get(chunk.id, 0) + 1.0 / (k + rank + 1)
        chunk_map[chunk.id] = chunk
        
    for rank, chunk in enumerate(keyword_chunks):
        scores[chunk.id] = scores.get(chunk.id, 0) + 1.0 / (k + rank + 1)
        chunk_map[chunk.id] = chunk

    # Sort by score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:limit]
    final_chunks = [chunk_map[cid] for cid in sorted_ids]
    
    # 5. Update Cache (TTL 1 hour)
    if final_chunks:
        await redis_client.setex(
            cache_key, 
            3600, 
            json.dumps([str(c.id) for c in final_chunks])
        )
    
    return final_chunks

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
