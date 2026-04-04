"""主应用入口测试：健康检查、路由注册、模型约束"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.db.models import ManagerProfile, PatientProfile
from app.main import app


@pytest.mark.asyncio
async def test_health_check_returns_structured_status():
    """增强版健康检查应返回 redis / database 结构化状态"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    data = response.json()
    assert "status" in data
    assert "redis" in data
    assert "database" in data
    # 测试环境依赖可能不可用，允许 503
    assert response.status_code in (200, 503)


@pytest.mark.asyncio
async def test_health_check_ok_when_deps_available():
    """当依赖可用时，健康检查应 status=ok"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    data = response.json()
    if data["redis"] == "ok" and data["database"] == "ok":
        assert data["status"] == "ok"
        assert response.status_code == 200


def test_kb_routes_registered():
    """知识库路由应正确注册"""
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/v1/kb" in paths or "/api/v1/kb/" in paths


def test_chat_routes_registered():
    """聊天路由应正确注册"""
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/v1/chat" in paths or "/api/v1/chat/" in paths


def test_patient_profile_unique_per_org():
    """PatientProfile 的唯一约束应为 (tenant_id, org_id, user_id)"""
    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in PatientProfile.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("tenant_id", "org_id", "user_id") in unique_constraints
    assert ("user_id",) not in unique_constraints


def test_manager_profile_unique_per_org():
    """ManagerProfile 的唯一约束应为 (tenant_id, org_id, user_id)"""
    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in ManagerProfile.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("tenant_id", "org_id", "user_id") in unique_constraints
    assert ("user_id",) not in unique_constraints
