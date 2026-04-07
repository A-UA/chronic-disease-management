"""审计日志服务 — 兼容导出层（阶段6清理时删除）

所有实际逻辑已迁移到 app.modules.audit.service
"""
from app.modules.audit.service import (  # noqa: F401
    audit_action,
    audit_action_async,
    fire_audit,
)
