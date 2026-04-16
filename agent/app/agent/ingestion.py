from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from app.config import settings

def process_document_to_milvus(file_bytes: bytes, filename: str, kb_id: str) -> int:
    text_content = file_bytes.decode('utf-8', errors='ignore')
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    texts = splitter.split_text(text_content)
    
    docs = [
        Document(
            page_content=txt,
            metadata={"kb_id": kb_id, "filename": filename, "source": filename}
        )
        for txt in texts
    ]
    
    if not docs:
        return 0

    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY
    )
    
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,
    )
    
    vector_store.add_documents(docs)
    return len(docs)
