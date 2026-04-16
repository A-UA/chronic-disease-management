"""RAG document ingestion pipeline.

The public ingestion entry now accepts injected runtime dependencies instead of
creating its own session or updating quota directly.
"""

import asyncio
import logging

from app.config import settings
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


async def ingest_document(
    milvus_store,
    document_id: int,
    kb_id: int,
    tenant_id: int,
    file_name: str,
    file_content: str,
    pages: list[str] | None = None,
    chunker=None,
    embedding_provider=None,
    llm_provider=None,
    contextual_ingestion: bool | None = None,
) -> tuple[int, int]:
    """Run ingestion using injected providers and write chunks into Milvus."""
    with trace_span("rag.ingest_document", {"document_id": document_id}):
        chunk_results = chunker.chunk(file_content, pages=pages)
        contextual_enabled = (
            settings.RAG_ENABLE_CONTEXTUAL_INGESTION
            if contextual_ingestion is None
            else contextual_ingestion
        )
        model_name = getattr(embedding_provider, "model_name", settings.EMBEDDING_MODEL)

        enhanced_contents: list[str] = []
        if contextual_enabled and llm_provider:
            tasks = [
                generate_chunk_context(file_content, cr.content, llm_provider)
                for cr in chunk_results
            ]
            contexts: list[str] = []
            for batch_start in range(0, len(tasks), 10):
                batch = tasks[batch_start : batch_start + 10]
                batch_results = await asyncio.gather(*batch)
                contexts.extend(batch_results)

            for cr, ctx in zip(chunk_results, contexts, strict=False):
                enhanced_contents.append(
                    f"{ctx}\n\n{cr.content}" if ctx else cr.content
                )
        else:
            enhanced_contents = [cr.content for cr in chunk_results]

        with trace_span("rag.embed_chunks", {"count": len(enhanced_contents)}):
            embeddings: list[list[float]] = []
            for batch_start in range(
                0, len(enhanced_contents), settings.EMBEDDING_BATCH_SIZE
            ):
                batch = enhanced_contents[
                    batch_start : batch_start + settings.EMBEDDING_BATCH_SIZE
                ]
                batch_embeddings = await embedding_provider.embed_documents(batch)
                embeddings.extend(batch_embeddings)

        actual_dim = embedding_provider.get_dimension()
        if actual_dim:
            logger.info("Processing document %s with dimension %s", document_id, actual_dim)
            await milvus_store.ensure_collection("kb", dimension=actual_dim)

        total_tokens = 0
        vectors_to_insert = []
        payloads_to_insert = []

        for index, (chunk_result, embedding, _enhanced_content) in enumerate(
            zip(chunk_results, embeddings, enhanced_contents, strict=False)
        ):
            num_tokens = count_tokens(chunk_result.content, model_name)
            total_tokens += num_tokens

            vectors_to_insert.append(embedding)
            payloads_to_insert.append({
                "document_id": document_id,
                "chunk_index": index,
                "content": chunk_result.content,
                "page_number": chunk_result.page_number or 0,
                "token_count": num_tokens,
                "section_title": chunk_result.section_title or "",
                "tenant_id": tenant_id,
                "kb_id": kb_id,
                # For Milvus, dynamic metadata needs to be serialized if we don't declare it
            })

        if vectors_to_insert:
            inserted_count = await milvus_store.insert(
                collection_name="kb",
                vectors=vectors_to_insert,
                payloads=payloads_to_insert
            )
            logger.info(f"Inserted {inserted_count} chunks into Milvus.")

        return total_tokens, len(chunk_results)
