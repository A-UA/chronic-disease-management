"""引用构建与提取

从 retrieval.py 拆分出的引用相关逻辑，包含：
- build_rag_prompt: 构建 RAG 提示词并生成引用列表
- build_statement_citations: 基于正则的声明-引用映射
- extract_statement_citations_structured: 基于 LLM 的结构化声明-引用映射
"""
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, TypedDict

from app.db.models import Chunk

if TYPE_CHECKING:
    from app.plugins.llm.base import LLMPlugin as LLMProvider

logger = logging.getLogger(__name__)

_DOC_REF_PATTERN = re.compile(
    r"(?:\[\s*Doc\s*(\d+)\s*\]|\bDoc\s*(\d+)\b)", re.IGNORECASE
)
_STATEMENT_BOUNDARY_PATTERN = re.compile(
    r"\n+|(?<=[。！？.!?])(?=\s*(?:Conclusion:|Evidence:|Uncertainty:))"
)


class Citation(TypedDict):
    doc_id: str
    chunk_id: str | None
    ref: str
    page: int | None
    chunk_index: int | None
    snippet: str
    source_span: dict[str, int]


class StatementCitation(TypedDict):
    text: str
    citations: list[Citation]


def _build_snippet_and_span(
    content: str, max_length: int = 120
) -> tuple[str, dict[str, int]]:
    if not content:
        return "", {"start": 0, "end": 0}

    start = 0
    while start < len(content) and content[start].isspace():
        start += 1

    end = len(content)
    while end > start and content[end - 1].isspace():
        end -= 1

    span_end = min(end, start + max_length)
    raw_snippet = content[start:span_end]
    if span_end < end:
        snippet = raw_snippet.rstrip() + "..."
    else:
        snippet = raw_snippet
    return snippet, {"start": start, "end": span_end}


def build_statement_citations(
    answer_text: str, citations: list[Citation]
) -> list[StatementCitation]:
    """基于正则的声明-引用映射"""
    ref_map = {citation["ref"].lower(): citation for citation in citations}
    statements: list[StatementCitation] = []
    for raw_part in _STATEMENT_BOUNDARY_PATTERN.split(answer_text):
        part = raw_part.strip()
        if not part:
            continue
        refs: list[str] = []
        for match in _DOC_REF_PATTERN.finditer(part):
            doc_number = match.group(1) or match.group(2)
            if doc_number is not None:
                refs.append(f"doc {doc_number}")
        mapped = [ref_map[ref] for ref in refs if ref in ref_map]
        statements.append({"text": part, "citations": mapped})
    return statements


async def extract_statement_citations_structured(
    answer_text: str,
    citations: list[Citation],
    llm_provider: LLMProvider,
) -> list[StatementCitation]:
    """基于 LLM 的结构化声明-引用映射（失败时 fallback 到正则）"""
    if not answer_text.strip():
        return []
    if not citations:
        return build_statement_citations(answer_text, citations)

    citation_refs = [
        {
            "ref": citation["ref"],
            "doc_id": citation["doc_id"],
            "chunk_id": citation.get("chunk_id"),
            "page": citation.get("page"),
        }
        for citation in citations
    ]
    prompt = (
        "Map each statement in the answer to the most relevant citation refs. "
        'Return strict JSON with shape {"statements":[{"text":"...","refs":["Doc 1"]}]}. '
        "Do not invent refs outside the provided citation list.\n\n"
        f"Available citations: {json.dumps(citation_refs, ensure_ascii=False)}\n"
        f"Answer: {answer_text}"
    )
    try:
        completion = await llm_provider.complete_text(prompt)
        parsed = json.loads(completion or "{}")
        items = parsed.get("statements", [])
        ref_map = {citation["ref"].lower(): citation for citation in citations}
        structured: list[StatementCitation] = []
        for item in items:
            text = (item.get("text") or "").strip()
            refs = [str(ref).lower() for ref in item.get("refs", [])]
            mapped = [ref_map[ref] for ref in refs if ref in ref_map]
            if text:
                structured.append({"text": text, "citations": mapped})
        if structured:
            return structured
    except Exception:
        logger.warning(
            "Structured statement citation extraction failed; falling back to regex mapping",
            exc_info=True,
        )

    return build_statement_citations(answer_text, citations)


def build_rag_prompt(
    query: str, chunks: list[Chunk], patient_name: str | None = None,
    language: str = "zh",
) -> tuple[str, list[dict[str, Citation]]]:
    """构建 RAG 提示词并生成引用列表"""
    context_blocks = []
    citations = []
    for i, chunk in enumerate(chunks):
        content = chunk.content
        if patient_name:
            content = content.replace(patient_name, "[PATIENT]")
        doc_ref = f"Doc {i + 1}"
        snippet, span = _build_snippet_and_span(content)
        context_blocks.append(f"[{doc_ref}] (page={chunk.page_number}): {content}")
        citations.append(
            {
                "doc_id": str(chunk.document_id),
                "chunk_id": str(chunk.id),
                "ref": doc_ref,
                "page": chunk.page_number,
                "snippet": snippet,
                "source_span": span,
            }
        )

    context_str = "\n\n".join(context_blocks)
    if patient_name:
        query = query.replace(patient_name, "[PATIENT]")

    if language == "zh":
        prompt = (
            "你是一个慢病管理临床推理助手。请严格基于以下「参考资料」回答问题。\n\n"
            "**规则：**\n"
            "1. 只使用参考资料中的信息，不得编造任何内容。\n"
            "2. 使用 **[Doc n]** 标注引用来源（n 为参考资料编号）。\n"
            "3. 若参考资料不足以回答，明确说明信息缺失，不要臆测。\n"
            "4. 使用中文回答。\n\n"
            "**格式要求：**\n"
            "- 使用 Markdown 格式输出，包括标题、列表、粗体等。\n"
            "- 先给出简洁结论，再展开详细分析。\n"
            "- 证据部分使用列表逐条列出，每条引用 [Doc n]。\n"
            "- 若存在不确定性，单独说明。\n\n"
            f"**参考资料：**\n{context_str}\n\n"
            f"**问题：** {query}\n\n"
        )
    else:
        prompt = (
            "You are a Chronic Disease Management Clinical Reasoning Assistant. "
            "Answer ONLY based on the provided Context.\n\n"
            "**Rules:**\n"
            "1. Use ONLY information from the Context. Never fabricate.\n"
            "2. Cite sources using **[Doc n]** notation.\n"
            "3. If Context is insufficient, clearly state what is missing.\n\n"
            "**Format:**\n"
            "- Use Markdown: headings, lists, bold, etc.\n"
            "- Lead with a concise conclusion, then expand with analysis.\n"
            "- List evidence with citations [Doc n].\n"
            "- Note any uncertainties separately.\n\n"
            f"**Context:**\n{context_str}\n\n"
            f"**Question:** {query}\n\n"
        )
    return prompt, citations
