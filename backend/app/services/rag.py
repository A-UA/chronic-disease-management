import io
import asyncio
from uuid import UUID
from sqlalchemy import func, select
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.db.models import Document, Chunk, UsageLog
from app.services.quota import update_org_quota
from typing import List

# Mock embedding for now, usually you'd use langchain_openai.OpenAIEmbeddings
class MockEmbeddings:
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Return dummy 1536-dimensional vectors
        return [[0.1] * 1536 for _ in texts]

embeddings_model = MockEmbeddings()

async def process_document(document_id: UUID, file_content: str):
    """
    Independent background processing of documents.
    Fetches its own DB session to avoid session closure from request scope.
    """
    async with AsyncSessionLocal() as db:
        # 1. Fetch document from DB
        document = await db.get(Document, document_id)
        if not document:
            return # Log error in production
            
        # 2. Advanced Text splitting (Medical Aware)
        # We use headers as separators to keep medical sections together
        separators = ["\n\n", "\n", "。", "！", "？", "；", "主诉:", "现病史:", "既往史:", "诊断:", "建议:", " "]
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            length_function=len,
            separators=separators
        )
        texts = text_splitter.split_text(file_content)
        
        # 3. Generate embeddings
        embeddings = embeddings_model.embed_documents(texts)
        
        # 4. Save Chunks with TSVector for Hybrid Search
        for i, (text, emb) in enumerate(zip(texts, embeddings)):
            chunk = Chunk(
                kb_id=document.kb_id,
                org_id=document.org_id,
                document_id=document.id,
                content=text,
                chunk_index=i,
                embedding=emb,
                # In Postgres, we use to_tsvector for keyword indexing
                tsv_content=func.to_tsvector('chinese', text)
            )
            db.add(chunk)
            
        # 5. Track Usage (dummy tokens calculation for demo)
        total_tokens = sum(len(t) // 4 for t in texts)
        usage = UsageLog(
            org_id=document.org_id,
            user_id=document.uploader_id,
            model="text-embedding-3-small",
            prompt_tokens=total_tokens,
            action_type="embedding",
            resource_id=document.id,
            cost=total_tokens * 0.00000002
        )
        db.add(usage)
        
        # 6. Update organization quota
        await update_org_quota(db, document.org_id, total_tokens)
        
        # 7. Update document status
        document.status = "completed"
        await db.commit()
