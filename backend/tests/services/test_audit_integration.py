"""P1-2: 审计日志集成测试

测试目标：
1. audit_action 应正确创建 AuditLog 记录
2. 支持可选字段（ip_address, details）
3. 不应自行 commit（由调用方控制事务）
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.audit import audit_action
from app.db.models import AuditLog


class TestAuditAction:
    @pytest.mark.asyncio
    async def test_creates_audit_log(self):
        """应创建一条 AuditLog 记录"""
        db = AsyncMock()
        db.add = MagicMock()

        await audit_action(
            db=db,
            user_id=1001,
            org_id=2001,
            action="login",
            resource_type="User",
        )
        db.add.assert_called_once()
        log = db.add.call_args[0][0]
        assert isinstance(log, AuditLog)
        assert log.user_id == 1001
        assert log.org_id == 2001
        assert log.action == "login"
        assert log.resource_type == "User"

    @pytest.mark.asyncio
    async def test_optional_fields(self):
        """ip_address 和 details 应为可选"""
        db = AsyncMock()
        db.add = MagicMock()

        await audit_action(
            db=db,
            user_id=1001,
            org_id=2001,
            action="upload_document",
            resource_type="Document",
            resource_id=3001,
            details='{"filename": "test.pdf"}',
            ip_address="192.168.1.1",
        )
        log = db.add.call_args[0][0]
        assert log.resource_id == 3001
        assert log.details == '{"filename": "test.pdf"}'
        assert log.ip_address == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_does_not_commit(self):
        """audit_action 不应自行 commit"""
        db = AsyncMock()
        db.add = MagicMock()

        await audit_action(
            db=db,
            user_id=1001,
            org_id=None,
            action="test",
            resource_type="Test",
        )
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_id_nullable(self):
        """org_id 可以为 None（跨组织操作）"""
        db = AsyncMock()
        db.add = MagicMock()

        await audit_action(
            db=db,
            user_id=1001,
            org_id=None,
            action="platform_login",
            resource_type="User",
        )
        log = db.add.call_args[0][0]
        assert log.org_id is None
