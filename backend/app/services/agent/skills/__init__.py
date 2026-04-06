"""Skills 包 — 导入时自动注册所有技能"""
from app.services.agent.skills.base import (
    SkillDefinition, SkillRegistry, SkillResult, skill_registry,
)

# 自动注册：导入模块即触发 skill_registry.register()
from app.services.agent.skills import rag_skill        # noqa: F401
from app.services.agent.skills import patient_skills    # noqa: F401
from app.services.agent.skills import calculator_skills # noqa: F401

__all__ = ["SkillDefinition", "SkillRegistry", "SkillResult", "skill_registry"]
