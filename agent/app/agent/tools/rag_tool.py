import re
import json
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from app.config import settings

# 正则表达式：用于校验 kb_id 格式，防止表达式注入攻击
_KB_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _get_vector_store() -> Milvus:
    """构建 Milvus 向量库连接（共享工厂方法）"""
    # 初始化嵌入模型
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )
    # 返回 Milvus 实例
    return Milvus(
        embedding_function=embeddings,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,
    )


@tool(response_format="content_and_artifact")  # 声明该工具返回 (展示内容, 结构化元数据) 模式
def rag_search_handler(query: str, config: RunnableConfig) -> tuple[str, list[dict]]:
    """在知识库中检索与问题相关的文档内容，返回带引用的上下文"""
    # 从运行时配置中获取 kb_id（由 Gateway 传入并透传至此）
    kb_id = config.get("configurable", {}).get("kb_id")
    if not kb_id:
        return "当前上下文中未找到知识库 ID，检索无法进行。", []

    # 安全校验：检查 kb_id 是否包含非法字符
    kb_id_str = str(kb_id)
    if not _KB_ID_PATTERN.match(kb_id_str):
        return "知识库 ID 格式不合法。", []

    # 获取向量库实例
    vector_store = _get_vector_store()

    # 构造检索参数：仅在指定的知识库范围内搜索
    search_kwargs = {"expr": f'kb_id == "{kb_id_str}"'}
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    # 执行相似度搜索
    docs = retriever.invoke(query)
    if not docs:
        return "该知识库中未找到与提问最相关的内容。", []

    # 构建返回数据
    context_parts = [] # 存储拼接后的文本内容
    citations = []     # 存储结构化引用信息
    for i, doc in enumerate(docs, 1):
        ref = f"[{i}]"
        source = doc.metadata.get("source", "未知来源")
        page = doc.metadata.get("page")
        snippet = doc.page_content[:200] # 摘要片段，方便前端展示

        # 拼接带编号的上下文
        context_parts.append(f"{ref} {doc.page_content}")
        # 封装引用详情
        citation = {"ref": ref, "source": source, "snippet": snippet}
        if page is not None:
            citation["page"] = page
        citations.append(citation)

    # 将所有文档块拼接为长文本供模型阅读
    context = "\n\n".join(context_parts)

    # content_and_artifact 模式：
    # 第一个返回值 (context) 将作为工具的回复内容注入 LLM 上下文
    # 第二个返回值 (citations) 将作为 artifact 被框架捕获，用于前端渲染引用卡片
    return context, citations
