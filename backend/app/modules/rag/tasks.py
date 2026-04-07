"""RAG 模块异步任务定义"""
import logging

logger = logging.getLogger(__name__)


async def process_document_task(ctx: dict, document_id: int, file_content: str, org_id: int, pages: list[str] | None = None):
    """arq 异步任务：文档入库

    Args:
        ctx: arq 上下文
        document_id: 文档 ID
        file_content: 文件文本内容
        org_id: 组织 ID
        pages: 按页拆分的文本列表（PDF 时可用）
    """
    logger.info("开始异步入库: doc=%s org=%s", document_id, org_id)
    from app.modules.rag.ingestion import process_document
    await process_document(document_id, file_content, org_id, pages=pages)
    logger.info("异步入库完成: doc=%s", document_id)


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
    """arq 异步任务：写入审计日志"""
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text
    from app.db.models.audit import AuditLog

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
