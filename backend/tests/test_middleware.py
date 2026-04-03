"""P0-1: 请求追踪中间件测试

测试目标：
1. 每个请求应自动生成 X-Request-ID
2. 客户端传入的 X-Request-ID 应被保留
3. 响应头中应包含 X-Request-ID
4. request_id 应在日志上下文中可用
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_response_contains_request_id_header():
    """响应头中应包含 X-Request-ID"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) > 0


@pytest.mark.asyncio
async def test_auto_generated_request_id_is_uuid():
    """自动生成的 request_id 应为有效的 UUID 格式"""
    import uuid
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
    rid = resp.headers["x-request-id"]
    # 应该不会抛异常
    parsed = uuid.UUID(rid)
    assert str(parsed) == rid


@pytest.mark.asyncio
async def test_preserves_client_request_id():
    """客户端传入的 X-Request-ID 应被保留"""
    custom_id = "client-trace-12345"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health", headers={"X-Request-ID": custom_id})
    assert resp.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
async def test_different_requests_get_different_ids():
    """不同请求应获得不同的 request_id"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp1 = await ac.get("/health")
        resp2 = await ac.get("/health")
    assert resp1.headers["x-request-id"] != resp2.headers["x-request-id"]
