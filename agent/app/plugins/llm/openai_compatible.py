"""OpenAI 兼容 LLM 插件实现"""

import logging

from langchain_openai import ChatOpenAI

from app.base.config import settings
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


def _create_llm_plugin() -> ChatOpenAI:
    if not settings.LLM_API_KEY:
        raise ValueError("请设置 LLM_API_KEY")
    if not settings.LLM_BASE_URL:
        raise ValueError("请设置 LLM_BASE_URL")
    logger.info(
        "LLM Plugin: model=%s, base_url=%s", settings.CHAT_MODEL, settings.LLM_BASE_URL
    )
    # 返回 LangChain 的 ChatOpenAI 实例，以原生支持 bind_tools
    return ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.CHAT_MODEL,
        temperature=0.7,
        streaming=True,  # 支持内部 streamEvents
    )


PluginRegistry.register("llm", "openai_compatible", _create_llm_plugin)
