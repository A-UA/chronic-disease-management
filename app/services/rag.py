import io
from uuid import UUID
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Document, Chunk, UsageLog
from typing import List

# Mock embedding for now, usually you'd use langchain_openai.OpenAIEmbeddings
class MockEmbeddings:
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Return dummy 1536-dimensional vectors
        return [[0.1] * 1536 for _ in texts]

embeddings_model = MockEmbeddings()

async def process_document(db: AsyncSession, document_id: UUID, file_content: str):
    # 1. Fetch document from DB
    document = await db.get(Document, document_id)
    if not document:
        raise ValueError("Document not found")
        
    # 2. Text splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    texts = text_splitter.split_text(file_content)
    
    # 3. Generate embeddings
    embeddings = embeddings_model.embed_documents(texts)
    
    # 4. Save Chunks
    for i, (text, emb) in enumerate(zip(texts, embeddings)):
        chunk = Chunk(
            kb_id=document.kb_id,
            org_id=document.org_id,
            document_id=document.id,
            content=text,
            chunk_index=i,
            embedding=emb
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
    
    # 6. Update document status
    document.status = "completed"
    await db.commit()
