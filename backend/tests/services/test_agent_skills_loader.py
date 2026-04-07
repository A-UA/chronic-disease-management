"""Agent Skills 加载器测试 — 遵循 agentskills.io 标准"""
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.agent.security import SecurityContext
from app.modules.agent.skills.base import SkillRegistry
from app.modules.agent.skills.markdown_loader import (
    parse_skill_md,
    load_skill_from_directory,
    register_skills_from_directory,
)

VALID_SKILL_MD = """\
---
name: test-skill
description: A test skill for unit testing. Use when running automated tests.
license: MIT
metadata:
  author: test
  version: "1.0"
  required-permission: chat:use
  parameters:
    query:
      type: string
      description: Test query
      required: true
---

# Test Skill

Follow these steps:
1. Parse the query
2. Return a result
"""

MINIMAL_SKILL_MD = """\
---
name: minimal-skill
description: Minimal valid skill.
---

Just do it.
"""


# --- parse_skill_md 测试 ---

class TestParseSkillMd:
    def test_valid_frontmatter(self):
        meta, body = parse_skill_md(VALID_SKILL_MD)
        assert meta["name"] == "test-skill"
        assert meta["description"].startswith("A test skill")
        assert meta["license"] == "MIT"
        assert meta["metadata"]["author"] == "test"
        assert "Follow these steps" in body

    def test_minimal(self):
        meta, body = parse_skill_md(MINIMAL_SKILL_MD)
        assert meta["name"] == "minimal-skill"

    def test_no_frontmatter_raises(self):
        with pytest.raises(ValueError, match="frontmatter"):
            parse_skill_md("no frontmatter here")

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            parse_skill_md("---\ndescription: no name\n---\nbody")

    def test_missing_description_raises(self):
        with pytest.raises(ValueError, match="description"):
            parse_skill_md("---\nname: test\n---\nbody")

    def test_invalid_name_uppercase(self):
        with pytest.raises(ValueError, match="小写"):
            parse_skill_md("---\nname: Bad-Name\ndescription: x\n---\nbody")

    def test_invalid_name_starts_with_hyphen(self):
        with pytest.raises(ValueError, match="连字符"):
            parse_skill_md("---\nname: -bad\ndescription: x\n---\nbody")

    def test_invalid_name_consecutive_hyphens(self):
        with pytest.raises(ValueError, match="小写"):
            parse_skill_md("---\nname: bad--name\ndescription: x\n---\nbody")


# --- load_skill_from_directory 测试 ---

class TestLoadSkillFromDirectory:
    def test_load_valid_skill(self):
        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td) / "test-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD, encoding="utf-8")

            skill = load_skill_from_directory(skill_dir)
            assert skill.name == "test-skill"
            assert skill.required_permission == "chat:use"
            assert "query" in skill.parameters_schema["properties"]

    def test_missing_skill_md_raises(self):
        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td) / "no-skill"
            skill_dir.mkdir()
            with pytest.raises(FileNotFoundError, match="SKILL.md"):
                load_skill_from_directory(skill_dir)

    def test_generates_openai_tool_schema(self):
        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td) / "test-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD, encoding="utf-8")

            skill = load_skill_from_directory(skill_dir)
            tool = skill.to_openai_tool_schema()
            assert tool["type"] == "function"
            assert tool["function"]["name"] == "test-skill"

    @pytest.mark.asyncio
    @patch("app.plugins.provider_compat.registry")
    async def test_handler_calls_llm(self, mock_registry):
        mock_llm = MagicMock()
        mock_llm.complete_text = AsyncMock(return_value="AI 回复")
        mock_registry.get_llm.return_value = mock_llm

        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td) / "test-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD, encoding="utf-8")

            skill = load_skill_from_directory(skill_dir)
            ctx = SecurityContext(tenant_id=1, org_id=2, user_id=3, db=MagicMock())
            result = await skill.handler(ctx, query="测试")

            assert result.success
            assert result.data == "AI 回复"
            prompt = mock_llm.complete_text.call_args[0][0]
            assert "Follow these steps" in prompt
            assert "测试" in prompt

    @pytest.mark.asyncio
    @patch("app.plugins.provider_compat.registry")
    async def test_handler_loads_references(self, mock_registry):
        """Level 3: references/ 目录内容自动附加到 prompt"""
        mock_llm = MagicMock()
        mock_llm.complete_text = AsyncMock(return_value="带参考的回复")
        mock_registry.get_llm.return_value = mock_llm

        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td) / "test-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD, encoding="utf-8")
            refs_dir = skill_dir / "references"
            refs_dir.mkdir()
            (refs_dir / "REFERENCE.md").write_text("参考：血压正常值 120/80", encoding="utf-8")

            skill = load_skill_from_directory(skill_dir)
            ctx = SecurityContext(tenant_id=1, org_id=2, user_id=3, db=MagicMock())
            await skill.handler(ctx, query="分析")

            prompt = mock_llm.complete_text.call_args[0][0]
            assert "120/80" in prompt


# --- register_skills_from_directory 测试 ---

class TestRegisterFromDirectory:
    def test_register_real_custom_skills(self):
        registry = SkillRegistry()
        custom_dir = Path(__file__).resolve().parents[2] / "app" / "services" / "agent" / "skills" / "custom"
        if custom_dir.exists():
            registered = register_skills_from_directory(registry, custom_dir)
            assert len(registered) >= 2
            names = {s.name for s in registered}
            assert "blood-pressure-analysis" in names
            assert "medication-reminder" in names

    def test_nonexistent_dir_returns_empty(self):
        registry = SkillRegistry()
        result = register_skills_from_directory(registry, "/nonexistent/dir")
        assert result == []

    def test_invalid_skills_skipped(self):
        registry = SkillRegistry()
        with tempfile.TemporaryDirectory() as td:
            # 无效目录（无 SKILL.md）
            (Path(td) / "bad-skill").mkdir()
            # 有效目录
            good_dir = Path(td) / "good-skill"
            good_dir.mkdir()
            (good_dir / "SKILL.md").write_text(
                "---\nname: good-skill\ndescription: Valid.\n---\nInstructions.",
                encoding="utf-8",
            )
            registered = register_skills_from_directory(registry, td)
            assert len(registered) == 1
            assert registered[0].name == "good-skill"
