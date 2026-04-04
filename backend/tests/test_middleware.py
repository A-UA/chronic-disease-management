"""中间件测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.core.middleware import RequestIDMiddleware


class TestRequestIDMiddleware:
    @pytest.mark.asyncio
    async def test_adds_request_id_header(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/test")

        assert r.status_code == 200
        assert "x-request-id" in r.headers

    @pytest.mark.asyncio
    async def test_preserves_existing_request_id(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/test", headers={"X-Request-ID": "my-custom-id"})

        assert r.status_code == 200
        assert r.headers.get("x-request-id") == "my-custom-id"
