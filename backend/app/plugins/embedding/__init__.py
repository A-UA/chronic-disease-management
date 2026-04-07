"""Embedding 插件包"""
from app.plugins.embedding.base import EmbeddingPlugin  # noqa: F401
import app.plugins.embedding.openai_compatible  # noqa: F401 — 触发注册
