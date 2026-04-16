"""Reranker 插件包"""

import app.plugins.reranker.noop  # noqa: F401 — 触发注册
import app.plugins.reranker.openai_compatible  # noqa: F401
import app.plugins.reranker.simple  # noqa: F401
from app.plugins.reranker.base import RerankerPlugin  # noqa: F401
