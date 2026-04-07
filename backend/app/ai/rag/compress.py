"""对话历史压缩服务

当对话历史超过阈值时，使用 LLM 生成摘要以减少后续请求的 Token 消耗。
"""
import logging

logger = logging.getLogger(__name__)

# 当历史消息超过此条数时触发压缩
COMPRESSION_THRESHOLD = 12

# 压缩后保留最近若干条原始消息
KEEP_RECENT_COUNT = 4


COMPRESSION_PROMPT = """请对以下对话历史生成一段简洁的中文摘要，保留关键信息（主题、结论、数据）。
摘要不超过 200 字，仅输出摘要内容，不要额外格式。

对话历史：
{history}
"""


def should_compress(messages: list[dict[str, str]]) -> bool:
    """判断是否需要对话压缩"""
    return len(messages) >= COMPRESSION_THRESHOLD


def build_compression_prompt(messages: list[dict[str, str]]) -> str:
    """构建压缩 prompt"""
    # 取出需要被压缩的早期消息
    to_compress = messages[:-KEEP_RECENT_COUNT]
    history_text = "\n".join(
        f"{'用户' if m['role'] == 'user' else 'AI'}: {m['content']}"
        for m in to_compress
    )
    return COMPRESSION_PROMPT.format(history=history_text)


async def compress_history(
    messages: list[dict[str, str]],
    llm_provider: object,
) -> list[dict[str, str]]:
    """压缩对话历史

    将 messages[:-KEEP_RECENT_COUNT] 压缩为一条 system 摘要消息，
    保留最近 KEEP_RECENT_COUNT 条原始消息。

    Args:
        messages: 完整对话历史
        llm_provider: 需实现 stream_text(prompt) 的 LLM provider

    Returns:
        压缩后的消息列表（摘要 + 最近消息）
    """
    if not should_compress(messages):
        return messages

    prompt = build_compression_prompt(messages)
    summary = ""

    try:
        async for chunk in llm_provider.stream_text(prompt):
            summary += chunk
    except Exception:
        logger.warning("对话压缩失败，返回原始历史（截断）")
        return messages[-KEEP_RECENT_COUNT:]

    if not summary.strip():
        return messages[-KEEP_RECENT_COUNT:]

    compressed = [
        {"role": "system", "content": f"[对话历史摘要] {summary.strip()}"},
        *messages[-KEEP_RECENT_COUNT:],
    ]

    logger.info(
        f"对话压缩：{len(messages)} 条 → {len(compressed)} 条（摘要 {len(summary)} 字）"
    )
    return compressed
