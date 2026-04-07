"""纯计算技能 — 无需权限，无需 DB 访问"""
from app.ai.agent.security import SecurityContext
from app.ai.agent.skills.base import SkillDefinition, SkillResult, skill_registry


async def bmi_calculator_handler(
    ctx: SecurityContext, height_cm: float = 0, weight_kg: float = 0,
) -> SkillResult:
    """根据身高体重计算 BMI 并判断等级"""
    if height_cm <= 0 or weight_kg <= 0:
        return SkillResult(success=False, error="身高和体重必须大于 0")
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        level = "偏瘦"
    elif bmi < 24:
        level = "正常"
    elif bmi < 28:
        level = "超重"
    else:
        level = "肥胖"
    return SkillResult(
        success=True,
        data={"bmi": bmi, "level": level, "height_cm": height_cm, "weight_kg": weight_kg},
    )


skill_registry.register(SkillDefinition(
    name="bmi_calculator",
    description="根据身高体重计算 BMI 并判断等级",
    parameters_schema={
        "type": "object",
        "properties": {
            "height_cm": {"type": "number", "description": "身高（厘米）"},
            "weight_kg": {"type": "number", "description": "体重（公斤）"},
        },
        "required": ["height_cm", "weight_kg"],
    },
    handler=bmi_calculator_handler,
    required_permission=None,
))
