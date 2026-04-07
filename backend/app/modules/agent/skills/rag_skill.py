"""RAG 检索技能 — 桥接现有的 retrieve_chunks + build_rag_prompt"""
from app.modules.agent.security import SecurityContext
from app.modules.agent.skills.base import SkillDefinition, SkillResult, skill_registry


async def rag_search_handler(
    ctx: SecurityContext, query: str = "", kb_id: int = 0,
) -> SkillResult:
    """在知识库中语义检索"""
    if not query or not kb_id:
        return SkillResult(success=False, error="需要 query 和 kb_id 参数")
    try:
        from app.modules.rag.chat_service import retrieve_chunks, build_rag_prompt
        from app.plugins.provider_compat import registry

        llm = registry.get_llm()
        chunks = await retrieve_chunks(
            db=ctx.db, query=query, kb_id=kb_id,
            org_id=ctx.org_id, user_id=ctx.user_id,
            llm_provider=llm,
        )
        if not chunks:
            return SkillResult(success=True, data="未找到相关文档内容")
        prompt, citations = build_rag_prompt(query, chunks)
        return SkillResult(success=True, data={
            "context": prompt, "citations": citations, "chunk_count": len(chunks),
        })
    except Exception as e:
        return SkillResult(success=False, error=str(e))


skill_registry.register(SkillDefinition(
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
))
