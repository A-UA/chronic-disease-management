from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.rag.llm_legacy import LLMProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedRetrievalQuery:
    original_query: str
    normalized_query: str
    retrieval_query: str


def normalize_query(query: str) -> str:
    """标准化查询：统一标点、去除多余空格"""
    normalized = query.strip().replace("？", "?").replace("，", ",").replace("：", ":")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


# 同义词/近义词扩展表：医疗场景常见的口语化表达 → 规范化检索词
_REWRITE_RULES: dict[str, str] = {
    # 用药相关
    "这个药还要继续吃吗": "用药是否需要继续",
    "这个药还能继续吃吗": "用药是否需要继续",
    "药能停吗": "是否可以停药",
    "可以停药吗": "是否可以停药",
    "药吃完了怎么办": "用药结束后如何处理",
    "有什么副作用": "药物不良反应",
    "有副作用吗": "药物不良反应",
    # 检查相关
    "这个指标高了怎么办": "指标异常处理建议",
    "指标偏高": "指标异常升高的临床意义",
    "指标偏低": "指标异常降低的临床意义",
    "报告看不懂": "检查报告解读",
    "结果正常吗": "检查结果是否在正常范围",
    # 症状相关
    "头疼怎么办": "头痛的诊疗建议",
    "肚子疼": "腹痛的鉴别诊断与处理",
    "发烧了": "发热的处理建议",
    "血压高了": "高血压的管理与治疗",
    "血糖高了": "血糖异常升高的处理",
    # 饮食/生活
    "能吃什么": "饮食建议与禁忌",
    "不能吃什么": "饮食禁忌",
    "需要忌口吗": "饮食禁忌与注意事项",
    "要注意什么": "日常注意事项与生活指导",
}

# 医疗术语别名映射：用于查询扩展
_MEDICAL_SYNONYMS: dict[str, list[str]] = {
    "高血压": ["血压升高", "血压偏高", "HBP", "hypertension"],
    "糖尿病": ["血糖异常", "DM", "diabetes"],
    "血脂": ["血脂异常", "高血脂", "血脂偏高", "dyslipidemia"],
    "心率": ["心跳", "脉搏", "pulse", "heart rate"],
    "BMI": ["体重指数", "体质指数", "body mass index"],
    "HbA1c": ["糖化血红蛋白", "糖化", "glycated hemoglobin"],
    "CT": ["CT检查", "CT扫描", "computed tomography"],
    "MRI": ["核磁共振", "磁共振", "magnetic resonance"],
    "ECG": ["心电图", "electrocardiogram"],
}


def _expand_medical_terms(query: str) -> str:
    """如果查询中包含医疗术语别名，在查询末尾追加规范术语以提升召回"""
    expansions: list[str] = []
    query_lower = query.lower()
    
    for canonical, aliases in _MEDICAL_SYNONYMS.items():
        # 如果查询中包含别名，追加规范词
        for alias in aliases:
            if alias.lower() in query_lower and canonical.lower() not in query_lower:
                expansions.append(canonical)
                break
        # 如果查询中包含规范词，追加常用别名
        if canonical.lower() in query_lower:
            for alias in aliases[:2]:  # 只取前两个最常用的别名
                if alias.lower() not in query_lower:
                    expansions.append(alias)
                    break
    
    if expansions:
        return f"{query} {' '.join(expansions)}"
    return query


def rewrite_query(normalized_query: str) -> str:
    """基于规则的查询改写 + 医疗术语扩展（支持模糊匹配）"""
    # 1. 精确匹配规则
    rewritten = _REWRITE_RULES.get(normalized_query)
    if rewritten:
        return _expand_medical_terms(rewritten)

    # 2. 模糊匹配：检查查询是否包含规则表中的关键短语
    best_match = None
    best_match_len = 0
    for pattern, replacement in _REWRITE_RULES.items():
        if pattern in normalized_query and len(pattern) > best_match_len:
            best_match = replacement
            best_match_len = len(pattern)

    if best_match:
        rewritten = best_match
    else:
        rewritten = normalized_query

    # 3. 医疗术语别名扩展
    rewritten = _expand_medical_terms(rewritten)
    return rewritten


async def rewrite_query_with_llm(query: str, llm_provider: LLMProvider) -> str:
    """使用 LLM 进行语义级查询改写（适用于复杂/模糊查询）
    
    当规则型改写无法处理时，可回退到此方法。
    成本较高，建议仅对短查询或明显模糊的查询使用。
    """
    prompt = (
        "你是一个医疗信息检索助手。将下面的口语化问题改写为适合在医疗知识库中检索的规范化查询词。\n"
        "只返回改写后的查询词，不要解释。如果问题已经足够清晰，则原样返回。\n\n"
        f"原始问题: {query}\n"
        "改写后的检索词:"
    )
    try:
        result = await llm_provider.complete_text(prompt)
        rewritten = result.strip()
        if rewritten and len(rewritten) < len(query) * 3:  # 防止 LLM 返回过长内容
            return rewritten
    except Exception:
        logger.warning("LLM query rewrite failed; using rule-based rewrite", exc_info=True)
    
    return query


def prepare_retrieval_query(query: str) -> PreparedRetrievalQuery:
    normalized_query = normalize_query(query)
    retrieval_query = rewrite_query(normalized_query)
    return PreparedRetrievalQuery(
        original_query=query,
        normalized_query=normalized_query,
        retrieval_query=retrieval_query,
    )
