"""Skills 包 — Python Skills 静态注册 + Agent Skills 标准目录动态注册"""
import logging
from pathlib import Path

from app.ai.agent.skills.base import (
    SkillDefinition,
    SkillRegistry,
    SkillResult,
    skill_registry,
)

logger = logging.getLogger(__name__)

# 1. 静态注册 Python Skills（导入即触发 skill_registry.register()）
from app.ai.agent.skills import (
    calculator_skills,  # noqa: F401
    patient_skills,  # noqa: F401
    rag_skill,  # noqa: F401
)

# 2. 动态注册 Agent Skills 标准目录（SKILL.md）
from app.ai.agent.skills.markdown_loader import register_skills_from_directory

_CUSTOM_SKILLS_DIR = Path(__file__).parent / "custom"
if _CUSTOM_SKILLS_DIR.is_dir():
    register_skills_from_directory(skill_registry, _CUSTOM_SKILLS_DIR)

__all__ = ["SkillDefinition", "SkillRegistry", "SkillResult", "skill_registry"]
