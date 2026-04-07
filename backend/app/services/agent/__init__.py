"""Agent module - compat export layer (remove in phase 6)

All logic has been migrated to app.modules.agent
"""
from app.modules.agent import SecurityContext, skill_registry, run_agent  # noqa: F401

__all__ = ["SecurityContext", "skill_registry", "run_agent"]
