"""切块策略插件包"""
from app.plugins.chunker.base import ChunkResult, ChunkerPlugin  # noqa: F401
import app.plugins.chunker.medical_heading  # noqa: F401 — 触发注册
