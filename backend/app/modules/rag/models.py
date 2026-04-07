"""RAG 模块模型导出

模型定义保留在 db/models/ 中以维护 Alembic 迁移兼容性，
此文件提供模块级别的统一导入入口。
"""
from app.db.models.knowledge import KnowledgeBase, Document, Chunk  # noqa: F401
from app.db.models.chat import Conversation, Message, UsageLog  # noqa: F401
