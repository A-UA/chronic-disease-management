"""密码修改与重置测试

覆盖：正确修改、错误旧密码、忘记密码、错误验证码
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import override_deps, make_user


def _make_app():
    from app.modules.auth.router import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    return app


class TestUpdatePassword:
    @pytest.mark.asyncio
    @patch("app.modules.auth.router.security.verify_password", return_value=True)
    @patch("app.modules.auth.router.security.get_password_hash", return_value="new_hash")
    async def test_change_password_ok(self, mock_hash, mock_verify):
        app = _make_app()
        user = make_user()
        db = AsyncMock()
        override_deps(app, db=db, user=user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.put("/api/v1/auth/update-password", json={
                "current_password": "OldPass123!",
                "new_password": "NewPass123!",
            })
        assert r.status_code == 200

    @pytest.mark.asyncio
    @patch("app.modules.auth.router.security.verify_password", return_value=False)
    async def test_wrong_current_password(self, mock_verify):
        app = _make_app()
        db = AsyncMock()
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.put("/api/v1/auth/update-password", json={
                "current_password": "WrongPass",
                "new_password": "NewPass123!",
            })
        assert r.status_code == 400


class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_always_200(self):
        """无论邮箱是否存在都返回200（防信息泄露）"""
        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        from app.api.deps import get_db
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/auth/forgot-password",
                              json={"email": "nonexistent@test.com"})
        assert r.status_code == 200


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_wrong_code_400(self):
        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        from app.api.deps import get_db
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/auth/reset-password", json={
                "email": "test@example.com",
                "code": "000000",
                "new_password": "NewPass123!",
            })
        assert r.status_code == 400


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_name(self):
        app = _make_app()
        user = make_user()
        db = AsyncMock()
        override_deps(app, db=db, user=user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.put("/api/v1/auth/me/profile", json={"name": "新姓名"})
        assert r.status_code == 200
        assert user.name == "新姓名"
