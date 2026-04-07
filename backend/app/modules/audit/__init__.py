"""Audit 模块 — 审计日志"""
# 模型
from app.db.models.audit import AuditLog  # noqa: F401

# 服务
from app.modules.audit.service import (  # noqa: F401
    audit_action,
    audit_action_async,
    fire_audit,
)

# 路由（按需导入，避免顶层循环依赖）
# from app.modules.audit.router import router
