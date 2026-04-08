"""RAG document ingestion pipeline.

The public ingestion entry now accepts injected runtime dependencies instead of
creating its own session or updating quota directly.
"""
import asyncio
import logging

from sqlalchemy import func

from app.base.config import settings
from app.models import Chunk, UsageLog
from app.plugins.chunker.medical_heading import count_tokens
from app.telemetry.tracing import trace_span

logger = logging.getLogger(__name__)


async def generate_chunk_context(
    document_content: str, chunk_content: str, llm_provider
) -> str:
    """Generate contextual retrieval text for a chunk."""
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


async def ingest_document_with_dependencies(
    *,
    db,
    document,
    file_content: str,
    pages: list[str] | None = None,
    chunker,
    embedding_provider,
    llm_provider,
    contextual_ingestion: bool | None = None,
) -> int:
    """Run ingestion using an injected session and injected providers."""
    with trace_span("rag.ingest_document", {"document_id": document.id}):
        chunk_results = chunker.chunk(file_content, pages=pages)
        contextual_enabled = (
            settings.RAG_ENABLE_CONTEXTUAL_INGESTION
            if contextual_ingestion is None
            else contextual_ingestion
        )
        model_name = getattr(embedding_provider, "model_name", settings.EMBEDDING_MODEL)

        enhanced_contents: list[str] = []
        if contextual_enabled:
            tasks = [
                generate_chunk_context(file_content, cr.content, llm_provider)
                for cr in chunk_results
            ]
            contexts: list[str] = []
            for batch_start in range(0, len(tasks), 10):
                batch = tasks[batch_start : batch_start + 10]
                batch_results = await asyncio.gather(*batch)
                contexts.extend(batch_results)

            for cr, ctx in zip(chunk_results, contexts):
                enhanced_contents.append(f"{ctx}\n\n{cr.content}" if ctx else cr.content)
        else:
            enhanced_contents = [cr.content for cr in chunk_results]

        with trace_span("rag.embed_chunks", {"count": len(enhanced_contents)}):
            embeddings: list[list[float]] = []
            for batch_start in range(0, len(enhanced_contents), settings.EMBEDDING_BATCH_SIZE):
                batch = enhanced_contents[
                    batch_start : batch_start + settings.EMBEDDING_BATCH_SIZE
                ]
                batch_embeddings = await embedding_provider.embed_documents(batch)
                embeddings.extend(batch_embeddings)

        actual_dim = embedding_provider.get_dimension()
        if actual_dim:
            logger.info(
                "Processing document %s with dimension %s",
                document.id,
                actual_dim,
            )

        total_tokens = 0
        for index, (chunk_result, embedding, enhanced_content) in enumerate(
            zip(chunk_results, embeddings, enhanced_contents)
        ):
            num_tokens = count_tokens(chunk_result.content, model_name)
            total_tokens += num_tokens

            db.add(
                Chunk(
                    tenant_id=document.tenant_id,
                    kb_id=document.kb_id,
                    org_id=document.org_id,
                    document_id=document.id,
                    content=chunk_result.content,
                    page_number=chunk_result.page_number,
                    chunk_index=index,
                    embedding=embedding,
                    tsv_content=func.to_tsvector("simple", enhanced_content),
                    metadata_={
                        "patient_id": str(document.patient_id)
                        if getattr(document, "patient_id", None)
                        else None,
                        "heading_aware": True,
                        "section_title": chunk_result.section_title,
                        "source": str(document.file_name) if document.file_name else "unknown",
                        "token_count": num_tokens,
                        "char_start": chunk_result.char_start,
                        "char_end": chunk_result.char_end,
                        "is_contextual": contextual_enabled,
                    },
                )
            )

        db.add(
            UsageLog(
                tenant_id=document.tenant_id,
                org_id=document.org_id,
                user_id=document.uploader_id,
                model=model_name,
                prompt_tokens=total_tokens,
                action_type="embedding",
                resource_id=document.id,
                cost=0.0,
            )
        )

        document.status = "completed"
        document.failed_reason = None
        return total_tokens
