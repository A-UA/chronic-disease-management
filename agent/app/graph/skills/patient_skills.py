"""患者相关 Skills — 所有数据访问通过 httpx 调用 Gateway"""

import httpx

from app.config import settings
from app.graph.security import SecurityContext
from app.graph.skills.base import SkillDefinition, SkillResult, skill_registry


async def query_patient_handler(
    ctx: SecurityContext,
    patient_id: int | None = None,
    name: str | None = None,
) -> SkillResult:
    """根据 ID 或姓名查询患者档案"""
    try:
        if not patient_id and not name:
            return SkillResult(success=False, error="请提供 patient_id 或 name")

        async with httpx.AsyncClient() as client:
            if patient_id:
                # Get precise patient profile
                response = await client.get(
                    f"{settings.GATEWAY_URL}/api/v1/patients/{patient_id}",
                    headers=ctx.auth_headers,
                    timeout=10.0,
                )
                if response.status_code == 404:
                    return SkillResult(success=True, data="未找到匹配的患者")
                response.raise_for_status()
                data = response.json()
                data = [data] # Wrap in list to match search format
            else:
                # Search patients by name
                response = await client.get(
                    f"{settings.GATEWAY_URL}/api/v1/patients",
                    params={"name": name, "page": 1, "size": 5},
                    headers=ctx.auth_headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json().get("content", [])
                if not data:
                    return SkillResult(success=True, data="未找到匹配的患者")

        # Map to succinct response for LLM
        formatted_data = [
            {
                "id": str(p["id"]),
                "name": p["name"],
                "gender": p.get("gender"),
                "primary_diagnosis": p.get("primaryDiagnosis"),
                "risk_level": p.get("riskLevel"),
            }
            for p in data
        ]
        return SkillResult(success=True, data=formatted_data)
    except httpx.HTTPStatusError as e:
        return SkillResult(success=False, error=f"Gateway HTTP Error: {e.response.status_code}")
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.GATEWAY_URL}/api/v1/health-metrics",
                params={
                    "patientId": patient_id,
                    "metricType": metric_type,
                },
                headers=ctx.auth_headers,
                timeout=10.0,
            )
            response.raise_for_status()
            content = response.json().get("content", [])

            if not content:
                return SkillResult(success=True, data=f"近 {days} 天无 {metric_type} 记录")

            # In the API response it is sorted by created time optionally, assuming descending or we limit to subset.
            metrics = content[:days]

        data = [
            {
                "date": m["recordedAt"],
                "value": m["metadata"],
                "type": m["metricType"],
            }
            for m in metrics
        ]
        return SkillResult(success=True, data=data)
    except httpx.HTTPStatusError as e:
        return SkillResult(success=False, error=f"Gateway HTTP Error: {e.response.status_code}")
    except Exception as e:
        return SkillResult(success=False, error=str(e))


skill_registry.register(
    SkillDefinition(
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
    )
)

skill_registry.register(
    SkillDefinition(
        name="health_trend",
        description="查询患者健康指标趋势（血压/血糖/体重/心率等）",
        parameters_schema={
            "type": "object",
            "properties": {
                "patient_id": {"type": "integer", "description": "患者 ID"},
                "metric_type": {
                    "type": "string",
                    "enum": [
                        "blood_pressure",
                        "blood_sugar",
                        "weight",
                        "heart_rate",
                        "bmi",
                        "spo2",
                    ],
                    "description": "指标类型",
                },
                "days": {"type": "integer", "description": "查询天数", "default": 30},
            },
            "required": ["patient_id"],
        },
        handler=health_trend_handler,
        required_permission="patient:read",
    )
)
