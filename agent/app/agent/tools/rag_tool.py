from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from app.config import settings

@tool
def rag_search_handler(query: str, config: RunnableConfig) -> str:
    """在知识库中检索与问题相关的文档内容，返回带引用的上下文"""
    kb_id = config.get("configurable", {}).get("kb_id")
    if not kb_id:
        return "当前上下文中未找到知识库 ID，检索无法进行。"
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
    
    # Restrict by kb_id
    search_kwargs = {"expr": f"kb_id == {kb_id}"}
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    
    docs = retriever.invoke(query)
    if not docs:
        return "该知识库中未找到与提问最相关的内容。"
    
    # Format and return references
    context = "\n\n".join([f"[引用] {doc.page_content}" for doc in docs])
    return context
