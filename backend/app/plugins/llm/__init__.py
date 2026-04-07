"""LLM 插件包"""
from app.plugins.llm.base import LLMPlugin  # noqa: F401
import app.plugins.llm.openai_compatible  # noqa: F401 — 触发注册
