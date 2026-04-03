"""P2-1: 密码修改接口测试

测试目标：
1. 旧密码正确时应成功修改
2. 旧密码错误时应返回 400
3. 新密码太短时应返回 422
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.deps import get_current_user, get_db
from app.api.endpoints.auth import router


def _make_app():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    return app


class TestPasswordChange:
    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """旧密码正确时应成功修改"""
        app = _make_app()

        user = MagicMock()
        user.id = 1001
        user.password_hash = "hashed_old"

        db = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: db

        with patch("app.core.security.verify_password", return_value=True), \
             patch("app.core.security.get_password_hash", return_value="hashed_new"):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.put("/api/v1/auth/update-password", json={
                    "current_password": "OldPass123!",
                    "new_password": "NewPass456!",
                })

        assert resp.status_code == 200
        assert user.password_hash == "hashed_new"

    @pytest.mark.asyncio
    async def test_wrong_old_password(self):
        """旧密码错误时应返回 400"""
        app = _make_app()

        user = MagicMock()
        user.id = 1001
        user.password_hash = "hashed_old"

        db = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: db

        with patch("app.core.security.verify_password", return_value=False):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.put("/api/v1/auth/update-password", json={
                    "current_password": "WrongPass",
                    "new_password": "NewPass456!",
                })

        assert resp.status_code == 400
