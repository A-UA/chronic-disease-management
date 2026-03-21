from uuid import UUID

from sqlalchemy import func

from app.db.models import Chunk, Document, UsageLog
from app.db.session import AsyncSessionLocal
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.quota import update_org_quota


MEDICAL_HEADINGS = (
    "主诉:",
    "主诉：",
    "现病史:",
    "现病史：",
    "既往史:",
    "既往史：",
    "个人史:",
    "个人史：",
    "过敏史:",
    "过敏史：",
    "查体:",
    "查体：",
    "辅助检查:",
    "辅助检查：",
    "诊断:",
    "诊断：",
    "处理意见:",
    "处理意见：",
    "建议:",
    "建议：",
)


def _split_long_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


def _merge_heading_paragraphs(paragraphs: list[str]) -> list[str]:
    merged: list[str] = []
    index = 0

    while index < len(paragraphs):
        current = paragraphs[index].strip()
        if current in MEDICAL_HEADINGS and index + 1 < len(paragraphs):
            merged.append(f"{current}\n{paragraphs[index + 1].strip()}")
            index += 2
            continue

        merged.append(current)
        index += 1

    return merged


def split_document_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    paragraphs = [paragraph.strip() for paragraph in normalized.split("\n\n") if paragraph.strip()]
    paragraphs = _merge_heading_paragraphs(paragraphs)
    chunks: list[str] = []

    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        if not lines:
            continue

        if lines[0] in MEDICAL_HEADINGS:
            paragraph = "\n".join(lines)

        if len(paragraph) <= chunk_size:
            chunks.append(paragraph)
        else:
            chunks.extend(_split_long_text(paragraph, chunk_size=chunk_size, chunk_overlap=chunk_overlap))

    return chunks


async def process_document(document_id: UUID, file_content: str):
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if not document:
            return

        texts = split_document_text(file_content)
        embedding_provider: EmbeddingProvider = get_embedding_provider()

        try:
            embeddings = embedding_provider.embed_documents(texts)

            for i, (text, emb) in enumerate(zip(texts, embeddings)):
                chunk = Chunk(
                    kb_id=document.kb_id,
                    org_id=document.org_id,
                    document_id=document.id,
                    content=text,
                    chunk_index=i,
                    embedding=emb,
                    tsv_content=func.to_tsvector("chinese", text),
                )
                db.add(chunk)

            total_tokens = sum(len(t) // 4 for t in texts)
            usage = UsageLog(
                org_id=document.org_id,
                user_id=document.uploader_id,
                model="text-embedding-3-small",
                prompt_tokens=total_tokens,
                action_type="embedding",
                resource_id=document.id,
                cost=total_tokens * 0.00000002,
            )
            db.add(usage)

            await update_org_quota(db, document.org_id, total_tokens)

            document.status = "completed"
            document.failed_reason = None
            await db.commit()
        except Exception as exc:
            document.status = "failed"
            document.failed_reason = str(exc)[:500]
            await db.commit()
