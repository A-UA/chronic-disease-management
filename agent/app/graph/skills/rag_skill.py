"""RAG 检索技能 — 桥接现有的 retrieve_chunks + build_rag_prompt"""

from app.graph.security import SecurityContext
from app.graph.skills.base import SkillDefinition, SkillResult, skill_registry


async def rag_search_handler(
    ctx: SecurityContext,
    query: str = "",
    kb_id: int = 0,
) -> SkillResult:
    """在知识库中语义检索"""
    if not query or not kb_id:
        return SkillResult(success=False, error="需要 query 和 kb_id 参数")

    from app.config import settings
    from app.plugins.registry import PluginRegistry
    from app.rag.retrieval import build_rag_prompt, retrieve_chunks
    from app.vectorstore.milvus import MilvusVectorStore

    milvus_store = MilvusVectorStore(
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
        collection_prefix=settings.MILVUS_COLLECTION_PREFIX,
    )

    try:
        llm_provider = PluginRegistry.get("llm")
        # In decoupled architecture, Gateway handles RBAC.
        # We rely on kb_id for scoping the Milvus query.
        org_id = 0
        user_id = 0

        chunks = await retrieve_chunks(
            milvus_store=milvus_store,
            query=query,
            kb_id=kb_id,
            org_id=org_id,
            user_id=user_id,
            limit=5,
            llm_provider=llm_provider,
        )

        if not chunks:
            return SkillResult(success=True, data="该知识库中未找到与提问最相关的内容。")

        prompt_context, _ = build_rag_prompt(query, chunks)
        # return the generated text prompt blocks
        return SkillResult(success=True, data=prompt_context)
    except Exception as e:
        return SkillResult(
            success=False,
            error=f"RAG 检索失败: {str(e)}"
        )


skill_registry.register(
    SkillDefinition(
        name="rag_search",
        description="在知识库中检索与问题相关的文档内容，返回带引用的上下文",
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索问题"},
                "kb_id": {"type": "integer", "description": "知识库 ID"},
            },
            "required": ["query", "kb_id"],
        },
        handler=rag_search_handler,
        required_permission="chat:use",
    )
)
