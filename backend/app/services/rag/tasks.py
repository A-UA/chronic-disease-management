"""RAG module async task definitions."""
import logging

logger = logging.getLogger(__name__)


async def enqueue_process_document_job(
    *,
    document_id: int,
    file_content: str,
    org_id: int,
    pages: list[str] | None = None,
) -> None:
    from arq import create_pool

    from app.tasks.worker import WorkerSettings

    redis = await create_pool(WorkerSettings.redis_settings)
    await redis.enqueue_job(
        "process_document_task",
        document_id,
        file_content,
        org_id,
        pages,
    )


async def enqueue_delete_file_job(*, minio_url: str) -> None:
    from arq import create_pool

    from app.tasks.worker import WorkerSettings

    redis = await create_pool(WorkerSettings.redis_settings)
    await redis.enqueue_job("delete_file_task", minio_url)


async def process_document_task(
    ctx: dict,
    document_id: int,
    file_content: str,
    org_id: int,
    pages: list[str] | None = None,
):
    """arq task: process a parsed document into chunks and embeddings."""
    from sqlalchemy import text

    from app.ai.rag.ingestion import ingest_document_with_dependencies
    from app.base.database import AsyncSessionLocal
    from app.models import Document
    from app.services.rag.provider_service import provider_service
    from app.services.system.quota import update_org_quota

    logger.info("Starting document ingestion task: doc=%s org=%s", document_id, org_id)

    async with AsyncSessionLocal() as db:
        await db.execute(
            text("SELECT set_config('app.current_org_id', :org_id, true)"),
            {"org_id": str(org_id)},
        )
        document = await db.get(Document, document_id)
        if not document:
            logger.error("Document %s not found during ingestion", document_id)
            return

        try:
            total_tokens = await ingest_document_with_dependencies(
                db=db,
                document=document,
                file_content=file_content,
                pages=pages,
                chunker=provider_service.get_chunker(),
                embedding_provider=provider_service.get_embedding(),
                llm_provider=provider_service.get_llm(),
            )
            await update_org_quota(db, document.org_id, total_tokens)
            await db.commit()
        except Exception as exc:
            logger.exception("Failed to process document %s", document_id)
            document.status = "failed"
            document.failed_reason = str(exc)[:500]
            await db.commit()
            raise

    logger.info("Document ingestion completed: doc=%s", document_id)


async def write_audit_log_task(
    ctx: dict,
    tenant_id: int,
    user_id: int,
    org_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    details: str | None = None,
):
    """arq task: persist an audit log entry."""
    from sqlalchemy import text

    from app.base.database import AsyncSessionLocal
    from app.models.audit import AuditLog

    async with AsyncSessionLocal() as db:
        if org_id:
            await db.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": str(org_id)},
            )
        log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        db.add(log)
        await db.commit()


async def delete_file_task(ctx: dict, minio_url: str):
    """arq task: delete a file from object storage."""
    from app.base.storage import get_storage_service

    await get_storage_service().delete_file(minio_url)
