"""患者相关 Skills — 所有数据访问通过 ctx.db（带 RLS）"""
from sqlalchemy import select

from app.models import HealthMetric, PatientProfile
from app.ai.agent.security import SecurityContext
from app.ai.agent.skills.base import SkillDefinition, SkillResult, skill_registry


async def query_patient_handler(
    ctx: SecurityContext, patient_id: int | None = None, name: str | None = None,
) -> SkillResult:
    """根据 ID 或姓名查询患者档案"""
    try:
        stmt = select(PatientProfile)
        if patient_id:
            stmt = stmt.where(PatientProfile.id == patient_id)
        elif name:
            stmt = stmt.where(PatientProfile.name.ilike(f"%{name}%"))
        else:
            return SkillResult(success=False, error="请提供 patient_id 或 name")
        result = await ctx.db.execute(stmt.limit(5))
        patients = result.scalars().all()
        if not patients:
            return SkillResult(success=True, data="未找到匹配的患者")
        data = [
            {
                "id": str(p.id),
                "name": p.name,
                "gender": p.gender,
                "primary_diagnosis": p.primary_diagnosis,
            }
            for p in patients
        ]
        return SkillResult(success=True, data=data)
    except Exception as e:
        return SkillResult(success=False, error=str(e))


async def health_trend_handler(
    ctx: SecurityContext,
    patient_id: int = 0,
    metric_type: str = "blood_pressure",
    days: int = 30,
) -> SkillResult:
    """查询患者健康指标趋势"""
    if not patient_id:
        return SkillResult(success=False, error="需要 patient_id")
    try:
        stmt = (
            select(HealthMetric)
            .where(
                HealthMetric.patient_id == patient_id,
                HealthMetric.metric_type == metric_type,
            )
            .order_by(HealthMetric.recorded_at.desc())
            .limit(days)
        )
        result = await ctx.db.execute(stmt)
        metrics = result.scalars().all()
        if not metrics:
            return SkillResult(success=True, data=f"近 {days} 天无 {metric_type} 记录")
        data = [
            {
                "date": m.recorded_at.isoformat(),
                "value": m.value,
                "type": m.metric_type,
            }
            for m in metrics
        ]
        return SkillResult(success=True, data=data)
    except Exception as e:
        return SkillResult(success=False, error=str(e))


skill_registry.register(SkillDefinition(
    name="query_patient",
    description="根据 ID 或姓名查询患者档案",
    parameters_schema={
        "type": "object",
        "properties": {
            "patient_id": {"type": "integer", "description": "患者 ID"},
            "name": {"type": "string", "description": "患者姓名（模糊搜索）"},
        },
    },
    handler=query_patient_handler,
    required_permission="patient:read",
))

skill_registry.register(SkillDefinition(
    name="health_trend",
    description="查询患者健康指标趋势（血压/血糖/体重/心率等）",
    parameters_schema={
        "type": "object",
        "properties": {
            "patient_id": {"type": "integer", "description": "患者 ID"},
            "metric_type": {
                "type": "string",
                "enum": ["blood_pressure", "blood_sugar", "weight", "heart_rate", "bmi", "spo2"],
                "description": "指标类型",
            },
            "days": {"type": "integer", "description": "查询天数", "default": 30},
        },
        "required": ["patient_id"],
    },
    handler=health_trend_handler,
    required_permission="patient:read",
))
