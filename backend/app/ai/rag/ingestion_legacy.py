import logging
import re
from dataclasses import dataclass
from functools import lru_cache

import tiktoken
from sqlalchemy import func

from app.base.config import settings
from app.models import Chunk, Document, UsageLog
from app.base.database import AsyncSessionLocal
from app.ai.rag.embeddings import EmbeddingProvider
from app.services.system.quota import update_org_quota
from app.plugins.provider_compat import registry

logger = logging.getLogger(__name__)

# 扩展后的医疗标题正则：覆盖常见病历、检验、影像、手术等文档节
MEDICAL_HEADING_RE = re.compile(
    r"^("
    r"主诉|现病史|既往史|个人史|家族史|过敏史|婚育史|月经史"
    r"|查体|体格检查|专科检查|神经系统检查"
    r"|辅助检查|实验室检查|化验结果|影像学检查|心电图|超声"
    r"|初步诊断|入院诊断|出院诊断|诊断依据|鉴别诊断"
    r"|治疗计划|治疗方案|治疗经过|处理意见|建议|医嘱|出院医嘱"
    r"|手术记录|手术名称|术中所见|术后处理"
    r"|护理记录|病程记录|会诊意见|病理报告"
    r")[:：\s]*$",
    re.MULTILINE,
)

# 中文句子边界正则：句号、问号、叹号、分号后跟空白或换行
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[。！？；\n])\s*")


@lru_cache(maxsize=16)
def _get_encoding(model_name: str = "gpt-4o"):
    """获取 tiktoken encoding 对象，使用 lru_cache 缓存避免重复创建"""
    try:
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model_name: str = "gpt-4o") -> int:
    """使用 tiktoken 精准计算 Token 数量（复用缓存的编码器）"""
    encoding = _get_encoding(model_name)
    return len(encoding.encode(text))


@dataclass(slots=True)
class ChunkWithMeta:
    """切块结果，携带页码和章节信息"""

    content: str
    page_number: int | None
    section_title: str | None
    char_start: int  # 在原文中的起始字符偏移量
    char_end: int  # 在原文中的结束字符偏移量


def _find_page_number(char_offset: int, page_boundaries: list[int]) -> int:
    """根据字符偏移量确定所在页码（1-indexed）"""
    for i, boundary in enumerate(page_boundaries):
        if char_offset < boundary:
            return i + 1
    return len(page_boundaries)


def _build_page_boundaries(pages: list[str]) -> list[int]:
    """构建每页文本的累积字符偏移量边界表

    当多页文本通过 '\\n\\n' 拼接后，根据每页长度 + 分隔符长度
    计算每页结束的累积字符位置。
    """
    boundaries: list[int] = []
    cumulative = 0
    for i, page_text in enumerate(pages):
        cumulative += len(page_text)
        if i < len(pages) - 1:
            cumulative += 2  # '\n\n' 分隔符
        boundaries.append(cumulative)
    return boundaries


def _split_by_sentences(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
    model_name: str,
    context_prefix: str = "",
    page_boundaries: list[int] | None = None,
    text_offset: int = 0,
) -> list[ChunkWithMeta]:
    """按句子边界切块，使用 token 数控制块大小

    改进点：
    1. 按句子边界切块，避免在中文句子中间断开
    2. 使用 token 数而非字符数控制块大小
    3. 保留页码信息
    """
    sentences = _SENTENCE_BOUNDARY_RE.split(text)
    sentences = [s for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[ChunkWithMeta] = []
    current_sentences: list[str] = []
    current_tokens = 0
    encoding = _get_encoding(model_name)
    prefix_tokens = len(encoding.encode(context_prefix + "\n")) if context_prefix else 0
    effective_max = max_tokens - prefix_tokens

    # 预计算每个句子的 token 数，避免循环中重复 encode
    sentence_token_counts: list[int] = [
        len(encoding.encode(sent)) for sent in sentences
    ]

    # 计算每个句子在 text 中的起始偏移量
    sentence_offsets: list[int] = []
    search_start = 0
    for sent in sentences:
        idx = text.find(sent, search_start)
        sentence_offsets.append(idx if idx >= 0 else search_start)
        search_start = (idx if idx >= 0 else search_start) + len(sent)

    def _flush_chunk(sents: list[str], first_sent_idx: int) -> ChunkWithMeta:
        raw_content = "".join(sents)
        final_content = (
            f"{context_prefix}\n{raw_content}" if context_prefix else raw_content
        )
        char_start = text_offset + sentence_offsets[first_sent_idx]
        last_sent_idx = first_sent_idx + len(sents) - 1
        char_end = text_offset + sentence_offsets[last_sent_idx] + len(sents[-1])

        page_num = None
        if page_boundaries:
            page_num = _find_page_number(char_start, page_boundaries)

        section = (
            context_prefix.replace("[章节: ", "").replace("]", "")
            if context_prefix
            else None
        )

        return ChunkWithMeta(
            content=final_content,
            page_number=page_num,
            section_title=section,
            char_start=char_start,
            char_end=char_end,
        )

    first_sent_idx = 0
    for i, sent in enumerate(sentences):
        sent_tokens = sentence_token_counts[i]

        # 如果单个句子就超过 max_tokens，强制作为独立 chunk
        if sent_tokens >= effective_max:
            if current_sentences:
                chunks.append(_flush_chunk(current_sentences, first_sent_idx))
                current_sentences = []
                current_tokens = 0
            chunks.append(_flush_chunk([sent], i))
            first_sent_idx = i + 1
            continue

        if current_tokens + sent_tokens > effective_max and current_sentences:
            chunks.append(_flush_chunk(current_sentences, first_sent_idx))

            # 重叠：从末尾保留 overlap_tokens 对应的句子
            overlap_sents: list[str] = []
            overlap_tok_count = 0
            for j in range(len(current_sentences) - 1, -1, -1):
                ot = sentence_token_counts[first_sent_idx + j]
                if overlap_tok_count + ot > overlap_tokens:
                    break
                overlap_sents.insert(0, current_sentences[j])
                overlap_tok_count += ot

            overlap_start = first_sent_idx + len(current_sentences) - len(overlap_sents)
            current_sentences = overlap_sents
            current_tokens = overlap_tok_count
            first_sent_idx = overlap_start

        if not current_sentences:
            first_sent_idx = i
        current_sentences.append(sent)
        current_tokens += sent_tokens

    if current_sentences:
        chunks.append(_flush_chunk(current_sentences, first_sent_idx))

    return chunks


def split_document_text(
    text: str,
    pages: list[str] | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[ChunkWithMeta]:
    """增强版切块：
    1. 识别医疗章节并保留上下文
    2. 按句子边界切块
    3. 保留页码信息
    4. 使用 token 数控制块大小（chunk_size 参数现在表示字符数阈值，
       内部换算为 token 数）
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    # 构建页面边界
    page_boundaries = _build_page_boundaries(pages) if pages else None

    # 粗略换算：中文约 1 字符 ≈ 1-2 token，取中间值
    # 建议后续直接传 token 数
    max_tokens = chunk_size // 2  # ~400 tokens（适合中文文档）
    overlap_tokens = chunk_overlap // 3  # ~50 tokens
    model_name = "gpt-4o"

    matches = list(MEDICAL_HEADING_RE.finditer(normalized))
    if not matches:
        return _split_by_sentences(
            normalized,
            max_tokens,
            overlap_tokens,
            model_name,
            page_boundaries=page_boundaries,
        )

    final_chunks: list[ChunkWithMeta] = []
    for i in range(len(matches)):
        start_pos = matches[i].start()
        heading = matches[i].group(1).strip()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
        section_content = normalized[start_pos:end_pos].strip()

        section_tokens = count_tokens(section_content, model_name)
        if section_tokens <= max_tokens:
            page_num = None
            if page_boundaries:
                page_num = _find_page_number(start_pos, page_boundaries)
            final_chunks.append(
                ChunkWithMeta(
                    content=section_content,
                    page_number=page_num,
                    section_title=heading,
                    char_start=start_pos,
                    char_end=end_pos,
                )
            )
        else:
            prefix = f"[章节: {heading}]"
            final_chunks.extend(
                _split_by_sentences(
                    section_content,
                    max_tokens,
                    overlap_tokens,
                    model_name,
                    context_prefix=prefix,
                    page_boundaries=page_boundaries,
                    text_offset=start_pos,
                )
            )
    return final_chunks


async def generate_chunk_context(
    document_content: str, chunk_content: str, llm_provider: "LLMProvider"
) -> str:
    """为切块生成背景上下文（Contextual Retrieval 技术）"""
    prompt = (
        "Here is a document: <document>\n"
        f"{document_content[:10000]}\n"  # 限制文档预览长度
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

            chunk_metas = split_document_text(file_content, pages=pages)
            embedding_provider: EmbeddingProvider = registry.get_embedding()
            llm_provider = registry.get_llm()
            model_name = getattr(embedding_provider, "model_name", settings.EMBEDDING_MODEL)

            # 增强：Contextual Ingestion
            enhanced_contents = []
            if settings.RAG_ENABLE_CONTEXTUAL_INGESTION:
                # 并行生成背景
                tasks = [
                    generate_chunk_context(file_content, cm.content, llm_provider)
                    for cm in chunk_metas
                ]
                # 分批执行，防止并发过大导致 Rate Limit
                batch_size = 10
                contexts = []
                for i in range(0, len(tasks), batch_size):
                    batch = tasks[i : i + batch_size]
                    batch_res = await asyncio.gather(*batch)
                    contexts.extend(batch_res)

                for cm, ctx in zip(chunk_metas, contexts):
                    if ctx:
                        # 将背景拼接到原始内容前面进行向量化
                        enhanced_contents.append(f"{ctx}\n\n{cm.content}")
                    else:
                        enhanced_contents.append(cm.content)
            else:
                enhanced_contents = [cm.content for cm in chunk_metas]

            # 向量化（分批处理，避免超出 API 限制）
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
            for i, (cm, emb, enhanced_content) in enumerate(
                zip(chunk_metas, embeddings, enhanced_contents)
            ):
                num_tokens = count_tokens(cm.content, model_name)
                total_tokens += num_tokens

                chunk = Chunk(
                    tenant_id=document.tenant_id,
                    kb_id=document.kb_id,
                    org_id=document.org_id,
                    document_id=document.id,
                    content=cm.content,
                    page_number=cm.page_number,
                    chunk_index=i,
                    embedding=emb,
                    tsv_content=func.to_tsvector("simple", enhanced_content),
                    metadata_={
                        "patient_id": str(document.patient_id)
                        if getattr(document, "patient_id", None)
                        else None,
                        "heading_aware": True,
                        "section_title": cm.section_title,
                        "source": str(document.file_name)
                        if document.file_name
                        else "unknown",
                        "token_count": num_tokens,
                        "char_start": cm.char_start,
                        "char_end": cm.char_end,
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

            # 统一计费和状态更新
            await update_org_quota(db, document.org_id, total_tokens)

            document.status = "completed"
            document.failed_reason = None
            await db.commit()
        except Exception as exc:
            logger.exception(f"Failed to process document {document_id}")
            # 这里需要重新获取 session 或者确保还能 commit
            try:
                # 重新获取 document 对象以防之前的 commit 失败或 session 状态问题
                # 但在同一个 async with 块中通常没问题
                document = await db.get(Document, document_id)
                if document:
                    document.status = "failed"
                    document.failed_reason = str(exc)[:500]
                    await db.commit()
            except Exception:
                logger.error("Double failure: could not even mark document as failed")
