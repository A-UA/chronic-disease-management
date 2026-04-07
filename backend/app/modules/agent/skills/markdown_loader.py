"""Agent Skills 加载器 — 遵循 agentskills.io 开放标准

标准结构：
  skill-name/
  ├── SKILL.md          # 必需：YAML frontmatter + 指令 body
  ├── scripts/          # 可选：可执行代码
  ├── references/       # 可选：参考文档
  └── assets/           # 可选：模板、资源

SKILL.md frontmatter 字段（标准）：
  - name: str          （必需）lowercase + hyphens, 1-64 chars
  - description: str   （必需）1-1024 chars
  - license: str       （可选）
  - compatibility: str （可选）
  - metadata: dict     （可选）
  - allowed-tools: str （可选）

扩展字段（项目自定义，放在 metadata 下）：
  - metadata.required-permission: str  权限代码

三级渐进加载：
  1. Discovery: 只加载 name + description（~100 tokens）
  2. Activation: 加载完整 SKILL.md body（< 5000 tokens）
  3. Execution: 按需加载 scripts/references/assets
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from app.modules.agent.security import SecurityContext
from app.modules.agent.skills.base import SkillDefinition, SkillRegistry, SkillResult

logger = logging.getLogger(__name__)

SKILL_FILENAME = "SKILL.md"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def parse_skill_md(content: str) -> tuple[dict[str, Any], str]:
    """解析 SKILL.md，返回 (frontmatter, body)"""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        raise ValueError("SKILL.md 必须以 YAML frontmatter (---) 开头")

    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        raise ValueError(f"YAML frontmatter 解析失败: {e}") from e

    if not isinstance(meta, dict):
        raise ValueError("YAML frontmatter 必须是字典格式")
    if "name" not in meta:
        raise ValueError("frontmatter 缺少必需字段: name")
    if "description" not in meta:
        raise ValueError("frontmatter 缺少必需字段: description")

    name = str(meta["name"])
    if len(name) < 1 or len(name) > 64:
        raise ValueError(f"name 长度必须在 1-64 之间: {name}")
    if not _NAME_RE.match(name):
        raise ValueError(
            f"name 只能包含小写字母、数字和连字符，不能以连字符开头/结尾: {name}"
        )

    desc = str(meta["description"])
    if len(desc) < 1 or len(desc) > 1024:
        raise ValueError("description 长度必须在 1-1024 之间")

    body = content[match.end():].strip()
    return meta, body


def _make_prompt_handler(instructions: str, skill_dir: Path | None = None):
    """创建 prompt-driven handler 闭包

    遵循 Agent Skills 三级加载：
    - instructions = SKILL.md body (Level 2: Activation)
    - skill_dir 用于按需加载 scripts/references/assets (Level 3: Execution)
    """

    async def handler(ctx: SecurityContext, **params: Any) -> SkillResult:
        from app.plugins.provider_compat import registry

        # 构建 prompt
        parts = [instructions]

        # Level 3: 如果有 references 目录，自动附加参考文档
        if skill_dir:
            refs_dir = skill_dir / "references"
            if refs_dir.is_dir():
                for ref_file in sorted(refs_dir.glob("*.md")):
                    try:
                        ref_content = ref_file.read_text(encoding="utf-8")
                        parts.append(f"\n--- 参考文档: {ref_file.name} ---\n{ref_content}")
                    except Exception:
                        pass

        if params:
            param_text = "\n".join(f"- {k}: {v}" for k, v in params.items())
            parts.append(f"\n--- 用户参数 ---\n{param_text}")

        parts.append("\n请基于以上指令和参数，用中文 Markdown 格式回答。")

        try:
            llm = registry.get_llm()
            response = await llm.complete_text("\n".join(parts))
            return SkillResult(success=True, data=response)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    return handler


def load_skill_from_directory(skill_dir: Path) -> SkillDefinition:
    """从标准 Agent Skills 目录加载 SkillDefinition

    Level 1 (Discovery): 解析 name + description
    Level 2 (Activation): 解析完整 SKILL.md body → handler
    """
    skill_file = skill_dir / SKILL_FILENAME
    if not skill_file.exists():
        raise FileNotFoundError(f"缺少 {SKILL_FILENAME}: {skill_dir}")

    content = skill_file.read_text(encoding="utf-8")
    meta, body = parse_skill_md(content)

    name = meta["name"]
    # 标准要求 name 必须匹配父目录名
    if skill_dir.name != name:
        logger.warning(
            "Skill name '%s' 与目录名 '%s' 不匹配（标准要求一致）",
            name, skill_dir.name,
        )

    # 从 metadata 扩展字段读取权限
    metadata = meta.get("metadata", {}) or {}
    required_permission = metadata.get("required-permission")

    # 参数 schema：从 metadata.parameters 读取（项目扩展）
    params_def = metadata.get("parameters", {})
    parameters_schema = _build_parameters_schema(params_def)

    return SkillDefinition(
        name=name,
        description=meta["description"],
        parameters_schema=parameters_schema,
        handler=_make_prompt_handler(body, skill_dir),
        required_permission=required_permission,
    )


def _build_parameters_schema(params_def: dict[str, Any] | None) -> dict[str, Any]:
    """参数定义 → JSON Schema"""
    if not params_def:
        return {"type": "object", "properties": {}}

    properties = {}
    required = []
    for name, spec in params_def.items():
        if not isinstance(spec, dict):
            continue
        prop: dict[str, Any] = {"type": spec.get("type", "string")}
        if "description" in spec:
            prop["description"] = spec["description"]
        if "enum" in spec:
            prop["enum"] = spec["enum"]
        properties[name] = prop
        if spec.get("required", False):
            required.append(name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def register_skills_from_directory(
    registry: SkillRegistry,
    base_dir: str | Path,
) -> list[SkillDefinition]:
    """扫描目录，每个含 SKILL.md 的子目录作为一个 Skill 注册

    目录结构：
      base_dir/
      ├── blood-pressure-analysis/
      │   └── SKILL.md
      ├── medication-reminder/
      │   ├── SKILL.md
      │   └── references/
      └── ...
    """
    base = Path(base_dir)
    if not base.is_dir():
        logger.warning("Skills 目录不存在: %s", base)
        return []

    registered = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        skill_file = child / SKILL_FILENAME
        if not skill_file.exists():
            continue
        try:
            skill = load_skill_from_directory(child)
            registry.register(skill)
            registered.append(skill)
            logger.info("注册 Agent Skill: %s (%s)", skill.name, child.name)
        except Exception:
            logger.warning("跳过无效 Skill 目录: %s", child, exc_info=True)

    if registered:
        logger.info(
            "从 %s 加载了 %d 个 Agent Skills: %s",
            base, len(registered),
            ", ".join(s.name for s in registered),
        )
    return registered
