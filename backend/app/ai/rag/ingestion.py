"""RAG 文档入库管线

保留 process_document 核心函数，切块逻辑委托给 chunker 插件，
旧的 split_document_text / ChunkWithMeta 保留以兼容外部调用。
"""
import asyncio
import logging

from sqlalchemy import func

from app.base.config import settings
from app.models import Chunk, Document, UsageLog
from app.base.database import AsyncSessionLocal
from app.services.system.quota import update_org_quota
from app.plugins.chunker.medical_heading import count_tokens
from app.plugins.provider_compat import registry
from app.plugins.registry import PluginRegistry
from app.telemetry.tracing import trace_span

logger = logging.getLogger(__name__)


# ── 兼容导出（旧代码可能直接使用这些符号） ──
from app.ai.rag.ingestion_legacy import (  # noqa: F401
    MEDICAL_HEADING_RE,
    ChunkWithMeta,
    split_document_text,
)


async def generate_chunk_context(
    document_content: str, chunk_content: str, llm_provider
) -> str:
    """为切块生成背景上下文（Contextual Retrieval 技术）"""
    prompt = (
        "Here is a document: <document>\n"
        f"{document_content[:10000]}\n"
        "</document>\n"
        "Here is a chunk from that document: <chunk>\n"
        f"{chunk_content}\n"
        "</chunk>\n"
        "Please give a short succinct context to situate this chunk within the overall document "
        "for the purpose of improving search retrieval of the chunk. "
        "Answer only with the context and nothing else."
    )
    try:
        context = await llm_provider.complete_text(prompt)
        return context.strip() if context else ""
    except Exception:
        logger.warning("Failed to generate chunk context; using empty string")
        return ""


async def process_document(
    document_id: int, file_content: str, org_id: int, pages: list[str] | None = None
):
    """处理文档入库：切块、生成 embedding、写入数据库"""
    with trace_span("rag.ingest_document", {"document_id": document_id}):
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text

            await db.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": str(org_id)},
            )

            try:
                document = await db.get(Document, document_id)
                if not document:
                    logger.error(f"Document {document_id} not found during ingestion")
                    return

                # 使用插件系统获取切块器
                chunker = PluginRegistry.get("chunker")
                chunk_results = chunker.chunk(file_content, pages=pages)

                embedding_provider = registry.get_embedding()
                llm_provider = registry.get_llm()
                model_name = getattr(embedding_provider, "model_name", settings.EMBEDDING_MODEL)

                # 增强：Contextual Ingestion
                enhanced_contents = []
                if settings.RAG_ENABLE_CONTEXTUAL_INGESTION:
                    tasks = [
                        generate_chunk_context(file_content, cr.content, llm_provider)
                        for cr in chunk_results
                    ]
                    batch_size = 10
                    contexts = []
                    for i in range(0, len(tasks), batch_size):
                        batch = tasks[i : i + batch_size]
                        batch_res = await asyncio.gather(*batch)
                        contexts.extend(batch_res)

                    for cr, ctx in zip(chunk_results, contexts):
                        if ctx:
                            enhanced_contents.append(f"{ctx}\n\n{cr.content}")
                        else:
                            enhanced_contents.append(cr.content)
                else:
                    enhanced_contents = [cr.content for cr in chunk_results]

                # 向量化（分批处理）
                with trace_span("rag.embed_chunks", {"count": len(enhanced_contents)}):
                    EMBEDDING_BATCH_SIZE = settings.EMBEDDING_BATCH_SIZE
                    embeddings: list[list[float]] = []
                    for batch_start in range(0, len(enhanced_contents), EMBEDDING_BATCH_SIZE):
                        batch = enhanced_contents[batch_start:batch_start + EMBEDDING_BATCH_SIZE]
                        batch_embeddings = await embedding_provider.embed_documents(batch)
                        embeddings.extend(batch_embeddings)

                actual_dim = embedding_provider.get_dimension()
                if actual_dim:
                    logger.info(
                        f"Processing document {document_id} with dimension {actual_dim}"
                    )

                total_tokens = 0
                for i, (cr, emb, enhanced_content) in enumerate(
                    zip(chunk_results, embeddings, enhanced_contents)
                ):
                    num_tokens = count_tokens(cr.content, model_name)
                    total_tokens += num_tokens

                    chunk = Chunk(
                        tenant_id=document.tenant_id,
                        kb_id=document.kb_id,
                        org_id=document.org_id,
                        document_id=document.id,
                        content=cr.content,
                        page_number=cr.page_number,
                        chunk_index=i,
                        embedding=emb,
                        tsv_content=func.to_tsvector("simple", enhanced_content),
                        metadata_={
                            "patient_id": str(document.patient_id)
                            if getattr(document, "patient_id", None)
                            else None,
                            "heading_aware": True,
                            "section_title": cr.section_title,
                            "source": str(document.file_name)
                            if document.file_name
                            else "unknown",
                            "token_count": num_tokens,
                            "char_start": cr.char_start,
                            "char_end": cr.char_end,
                            "is_contextual": settings.RAG_ENABLE_CONTEXTUAL_INGESTION,
                        },
                    )
                    db.add(chunk)

                usage = UsageLog(
                    tenant_id=document.tenant_id,
                    org_id=document.org_id,
                    user_id=document.uploader_id,
                    model=model_name,
                    prompt_tokens=total_tokens,
                    action_type="embedding",
                    resource_id=document.id,
                    cost=0.0,
                )
                db.add(usage)

                await update_org_quota(db, document.org_id, total_tokens)

                document.status = "completed"
                document.failed_reason = None
                await db.commit()
            except Exception as exc:
                logger.exception(f"Failed to process document {document_id}")
                try:
                    document = await db.get(Document, document_id)
                    if document:
                        document.status = "failed"
                        document.failed_reason = str(exc)[:500]
                        await db.commit()
                except Exception:
                    logger.error("Double failure: could not even mark document as failed")
