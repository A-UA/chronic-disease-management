import re
import logging
from uuid import UUID

from sqlalchemy import func

from app.db.models import Chunk, Document, UsageLog
from app.db.session import AsyncSessionLocal
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.quota import update_org_quota

logger = logging.getLogger(__name__)

# 更全的医疗标题正则
MEDICAL_HEADING_RE = re.compile(
    r"^(主诉|现病史|既往史|个人史|家族史|过敏史|查体|辅助检查|初步诊断|诊断依据|鉴别诊断|治疗计划|处理意见|建议|医嘱)[:：\s]*$",
    re.MULTILINE
)

def _split_with_context(text: str, chunk_size: int, chunk_overlap: int, context_prefix: str = "") -> list[str]:
    """带有上下文前缀的物理切块"""
    effective_chunk_size = chunk_size - len(context_prefix) - 5
    if effective_chunk_size <= 100: # 前缀太长了
        effective_chunk_size = chunk_size // 2
        
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + effective_chunk_size, len(text))
        chunk_content = text[start:end]
        
        # 拼装前缀
        final_content = f"{context_prefix}\n{chunk_content}" if context_prefix else chunk_content
        chunks.append(final_content)
        
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks

def split_document_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    """增强版切块：识别医疗章节并保留上下文"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    # 1. 识别所有章节位置
    matches = list(MEDICAL_HEADING_RE.finditer(normalized))
    if not matches:
        # 没有识别到章节，退化为普通物理切块
        return _split_with_context(normalized, chunk_size, chunk_overlap)

    final_chunks: list[str] = []
    
    # 2. 按章节切割
    for i in range(len(matches)):
        start_pos = matches[i].start()
        heading = matches[i].group(1).strip()
        
        # 确定本章节结束位置
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(normalized)
        section_content = normalized[start_pos:end_pos].strip()
        
        if len(section_content) <= chunk_size:
            final_chunks.append(section_content)
        else:
            # 章节内部进行带前缀的切割，前缀包含当前章节标题
            prefix = f"[章节: {heading}]"
            final_chunks.extend(_split_with_context(section_content, chunk_size, chunk_overlap, context_prefix=prefix))
            
    return final_chunks

async def process_document(document_id: UUID, file_content: str):
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if not document:
            return

        texts = split_document_text(file_content)
        embedding_provider: EmbeddingProvider = get_embedding_provider()

        try:
            embeddings = embedding_provider.embed_documents(texts)
            
            # 记录维度校检（可选，基于 1.1 的 get_dimension）
            actual_dim = embedding_provider.get_dimension()
            if actual_dim:
                logger.info(f"Processing document {document_id} with embedding dimension: {actual_dim}")

            for i, (text, emb) in enumerate(zip(texts, embeddings)):
                chunk = Chunk(
                    kb_id=document.kb_id,
                    org_id=document.org_id,
                    document_id=document.id,
                    content=text,
                    chunk_index=i,
                    embedding=emb,
                    tsv_content=func.to_tsvector("chinese", text),
                    # metadata 字段用于存储结构化信息，支持我们刚在 chat.py 写的 dynamic filter
                    metadata={
                        "heading_aware": True,
                        "source": str(document.file_name) if document.file_name else "unknown"
                    }
                )
                db.add(chunk)

            # Token 统计改进（使用 tiktoken 如果可用，或者估算）
            total_tokens = sum(len(t) // 2 for t in texts) # 简单估算，中文约 2 字节/token
            
            usage = UsageLog(
                org_id=document.org_id,
                user_id=document.uploader_id,
                model=getattr(embedding_provider, "model_name", "unknown"),
                prompt_tokens=total_tokens,
                action_type="embedding",
                resource_id=document.id,
                cost=0.0 # 实际成本由结算系统计算
            )
            db.add(usage)

            await update_org_quota(db, document.org_id, total_tokens)

            document.status = "completed"
            document.failed_reason = None
            await db.commit()
        except Exception as exc:
            logger.exception(f"Failed to process document {document_id}")
            document.status = "failed"
            document.failed_reason = str(exc)[:500]
            await db.commit()
