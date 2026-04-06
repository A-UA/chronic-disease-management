"""Skills 框架：定义、注册、权限过滤、安全执行"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from app.services.agent.security import SecurityContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SkillResult:
    """Skill 执行结果"""
    success: bool
    data: Any = None
    error: str | None = None

    def to_context_string(self) -> str:
        """转换为可插入 prompt 的上下文字符串"""
        if not self.success:
            return f"[技能执行失败: {self.error}]"
        if isinstance(self.data, str):
            return self.data
        return json.dumps(self.data, ensure_ascii=False, default=str)


# Skill handler 签名
SkillHandler = Callable[..., Awaitable[SkillResult]]


@dataclass(slots=True)
class SkillDefinition:
    """Skill 注册定义"""
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: SkillHandler
    required_permission: str | None = None

    def to_openai_tool_schema(self) -> dict:
        """生成 OpenAI Function Calling 兼容的 tool schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


class SkillRegistry:
    """Skill 注册表"""

    def __init__(self):
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        """注册技能"""
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def list_all(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def get_available(self, permissions: frozenset[str]) -> list[SkillDefinition]:
        """根据权限过滤可用 Skills"""
        return [
            s for s in self._skills.values()
            if s.required_permission is None or s.required_permission in permissions
        ]

    def get_tool_schemas(self, permissions: frozenset[str]) -> list[dict]:
        """生成当前用户可用的 function calling schemas"""
        return [s.to_openai_tool_schema() for s in self.get_available(permissions)]

    async def execute(
        self, name: str, ctx: SecurityContext, params: dict[str, Any],
    ) -> SkillResult:
        """安全执行 Skill：权限预校验 + 参数白名单"""
        skill = self.get(name)
        if skill is None:
            return SkillResult(success=False, error=f"未知技能: {name}")

        # 权限预校验
        if skill.required_permission and not ctx.has_permission(skill.required_permission):
            return SkillResult(
                success=False,
                error=f"权限不足: 需要 {skill.required_permission}",
            )

        # 参数白名单过滤
        allowed = set(skill.parameters_schema.get("properties", {}).keys())
        safe_params = {k: v for k, v in params.items() if k in allowed}

        try:
            return await skill.handler(ctx, **safe_params)
        except Exception as e:
            logger.error("Skill %s 执行失败", name, exc_info=True)
            return SkillResult(success=False, error=str(e))


# 全局单例
skill_registry = SkillRegistry()
