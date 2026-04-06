"""业务 Skills 测试"""
import pytest
from unittest.mock import MagicMock
from app.services.agent.security import SecurityContext
from app.services.agent.skills.calculator_skills import bmi_calculator_handler


def _ctx(perms=frozenset()):
    return SecurityContext(tenant_id=1, org_id=2, user_id=3,
                           permissions=perms, db=MagicMock())


class TestBMICalculator:
    @pytest.mark.asyncio
    async def test_normal_bmi(self):
        res = await bmi_calculator_handler(_ctx(), height_cm=170, weight_kg=65)
        assert res.success
        assert res.data["bmi"] == 22.5
        assert res.data["level"] == "正常"

    @pytest.mark.asyncio
    async def test_obese_bmi(self):
        res = await bmi_calculator_handler(_ctx(), height_cm=170, weight_kg=90)
        assert res.success
        assert res.data["level"] == "肥胖"

    @pytest.mark.asyncio
    async def test_underweight_bmi(self):
        res = await bmi_calculator_handler(_ctx(), height_cm=170, weight_kg=50)
        assert res.success
        assert res.data["level"] == "偏瘦"

    @pytest.mark.asyncio
    async def test_invalid_input(self):
        res = await bmi_calculator_handler(_ctx(), height_cm=0, weight_kg=70)
        assert not res.success
        assert "大于 0" in res.error
