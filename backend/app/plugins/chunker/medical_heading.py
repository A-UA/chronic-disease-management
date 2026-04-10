"""医疗文档标题感知切块策略插件

从 services/rag_ingestion.py 提取的核心切块逻辑，
保留医疗标题识别、句子边界切块、token 计数控制、页码追踪等全部功能。
"""

import logging
import re
from functools import lru_cache

import tiktoken

from app.plugins.chunker.base import ChunkResult
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

# 扩展后的医疗标题正则
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

# 中文句子边界
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[。！？；\n])\s*")


@lru_cache(maxsize=16)
def _get_encoding(model_name: str = "gpt-4o"):
    try:
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model_name: str = "gpt-4o") -> int:
    encoding = _get_encoding(model_name)
    return len(encoding.encode(text))


def _find_page_number(char_offset: int, page_boundaries: list[int]) -> int:
    for i, boundary in enumerate(page_boundaries):
        if char_offset < boundary:
            return i + 1
    return len(page_boundaries)


def _build_page_boundaries(pages: list[str]) -> list[int]:
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
) -> list[ChunkResult]:
    sentences = _SENTENCE_BOUNDARY_RE.split(text)
    sentences = [s for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[ChunkResult] = []
    current_sentences: list[str] = []
    current_tokens = 0
    encoding = _get_encoding(model_name)
    prefix_tokens = len(encoding.encode(context_prefix + "\n")) if context_prefix else 0
    effective_max = max_tokens - prefix_tokens

    sentence_token_counts: list[int] = [
        len(encoding.encode(sent)) for sent in sentences
    ]

    sentence_offsets: list[int] = []
    search_start = 0
    for sent in sentences:
        idx = text.find(sent, search_start)
        sentence_offsets.append(idx if idx >= 0 else search_start)
        search_start = (idx if idx >= 0 else search_start) + len(sent)

    def _flush_chunk(sents: list[str], first_sent_idx: int) -> ChunkResult:
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

        return ChunkResult(
            content=final_content,
            page_number=page_num,
            section_title=section,
            char_start=char_start,
            char_end=char_end,
        )

    first_sent_idx = 0
    for i, sent in enumerate(sentences):
        sent_tokens = sentence_token_counts[i]

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


class MedicalHeadingChunkerPlugin:
    """医疗标题感知切块策略"""

    name = "medical_heading"

    def chunk(
        self,
        text: str,
        pages: list[str] | None = None,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ) -> list[ChunkResult]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return []

        page_boundaries = _build_page_boundaries(pages) if pages else None
        max_tokens = chunk_size // 2
        overlap_tokens = chunk_overlap // 3
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

        final_chunks: list[ChunkResult] = []
        for i in range(len(matches)):
            start_pos = matches[i].start()
            heading = matches[i].group(1).strip()
            end_pos = (
                matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
            )
            section_content = normalized[start_pos:end_pos].strip()

            section_tokens = count_tokens(section_content, model_name)
            if section_tokens <= max_tokens:
                page_num = None
                if page_boundaries:
                    page_num = _find_page_number(start_pos, page_boundaries)
                final_chunks.append(
                    ChunkResult(
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


PluginRegistry.register(
    "chunker", "medical_heading", lambda: MedicalHeadingChunkerPlugin()
)
