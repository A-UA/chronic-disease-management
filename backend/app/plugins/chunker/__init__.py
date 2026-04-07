"""切块策略插件包"""
import app.plugins.chunker.medical_heading  # noqa: F401 — 触发注册
from app.plugins.chunker.base import ChunkerPlugin, ChunkResult  # noqa: F401
