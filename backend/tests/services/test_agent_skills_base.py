"""Skills 基础设施测试"""
import pytest
from app.services.agent.security import SecurityContext
from app.services.agent.skills.base import SkillDefinition, SkillRegistry, SkillResult


async def _echo(ctx, message=""):
    return SkillResult(success=True, data=f"echo:{message}")


async def _boom(ctx):
    raise RuntimeError("boom")


def _ctx(perms=frozenset()):
    return SecurityContext(tenant_id=1, org_id=2, user_id=3, permissions=perms)


ECHO = SkillDefinition(
    name="echo", description="回显", handler=_echo,
    parameters_schema={"type": "object", "properties": {"message": {"type": "string"}}},
)
PROTECTED = SkillDefinition(
    name="protected", description="受保护", handler=_echo,
    parameters_schema={"type": "object", "properties": {}},
    required_permission="admin:manage",
)


class TestSkillRegistry:
    def test_register_and_get(self):
        r = SkillRegistry()
        r.register(ECHO)
        assert r.get("echo") is ECHO

    def test_filter_by_permission(self):
        r = SkillRegistry()
        r.register(ECHO)
        r.register(PROTECTED)
        assert len(r.get_available(frozenset())) == 1
        assert len(r.get_available(frozenset({"admin:manage"}))) == 2

    @pytest.mark.asyncio
    async def test_execute_success(self):
        r = SkillRegistry()
        r.register(ECHO)
        res = await r.execute("echo", _ctx(), {"message": "hi"})
        assert res.success and res.data == "echo:hi"

    @pytest.mark.asyncio
    async def test_execute_permission_denied(self):
        r = SkillRegistry()
        r.register(PROTECTED)
        res = await r.execute("protected", _ctx(), {})
        assert not res.success and "权限不足" in res.error

    @pytest.mark.asyncio
    async def test_execute_unknown(self):
        res = await SkillRegistry().execute("nope", _ctx(), {})
        assert not res.success

    @pytest.mark.asyncio
    async def test_params_whitelist(self):
        r = SkillRegistry()
        r.register(ECHO)
        res = await r.execute("echo", _ctx(), {"message": "hi", "evil": "drop"})
        assert res.success

    @pytest.mark.asyncio
    async def test_handler_exception(self):
        r = SkillRegistry()
        r.register(SkillDefinition(
            name="fail", description="", handler=_boom,
            parameters_schema={"type": "object", "properties": {}},
        ))
        res = await r.execute("fail", _ctx(), {})
        assert not res.success and "boom" in res.error


class TestSkillResult:
    def test_to_context_string_success_str(self):
        r = SkillResult(success=True, data="hello")
        assert r.to_context_string() == "hello"

    def test_to_context_string_failure(self):
        r = SkillResult(success=False, error="oops")
        assert "失败" in r.to_context_string()
