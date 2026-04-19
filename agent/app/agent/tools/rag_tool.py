import re
import json
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from app.config import settings

_KB_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _get_vector_store() -> Milvus:
    """构建 Milvus 向量库连接（共享工厂方法）"""
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )
    return Milvus(
        embedding_function=embeddings,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,
    )


@tool(response_format="content_and_artifact")  # type: ignore[arg-type]
def rag_search_handler(query: str, config: RunnableConfig) -> tuple[str, list[dict]]:
    """在知识库中检索与问题相关的文档内容，返回带引用的上下文"""
    kb_id = config.get("configurable", {}).get("kb_id")
    if not kb_id:
        return "当前上下文中未找到知识库 ID，检索无法进行。", []

    # 安全校验：防止表达式注入
    kb_id_str = str(kb_id)
    if not _KB_ID_PATTERN.match(kb_id_str):
        return "知识库 ID 格式不合法。", []

    vector_store = _get_vector_store()

    # 使用受控表达式过滤
    search_kwargs = {"expr": f'kb_id == "{kb_id_str}"'}
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    docs = retriever.invoke(query)
    if not docs:
        return "该知识库中未找到与提问最相关的内容。", []

    # 构建文本上下文
    context_parts = []
    citations = []
    for i, doc in enumerate(docs, 1):
        ref = f"[{i}]"
        source = doc.metadata.get("source", "未知来源")
        page = doc.metadata.get("page")
        snippet = doc.page_content[:200]

        context_parts.append(f"{ref} {doc.page_content}")
        citation = {"ref": ref, "source": source, "snippet": snippet}
        if page is not None:
            citation["page"] = page
        citations.append(citation)

    context = "\n\n".join(context_parts)

    # content_and_artifact 模式：返回 (文本内容, 结构化引用数据)
    return context, citations
