"""B6-B10 新服务层测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestRerankerProviderFactory:
    """B6: Reranker provider 工厂测试"""

    def test_noop_provider(self):
        with patch("app.services.reranker.settings") as s:
            s.RERANKER_PROVIDER = "noop"
            from app.services.reranker import get_reranker_provider, NoopRerankerProvider
            p = get_reranker_provider()
            assert isinstance(p, NoopRerankerProvider)

    def test_simple_provider(self):
        with patch("app.services.reranker.settings") as s:
            s.RERANKER_PROVIDER = "simple"
            from app.services.reranker import get_reranker_provider, SimpleRerankerProvider
            p = get_reranker_provider()
            assert isinstance(p, SimpleRerankerProvider)

    def test_zhipu_provider(self):
        with patch("app.services.reranker.settings") as s:
            s.RERANKER_PROVIDER = "zhipu"
            s.RERANKER_API_KEY = "test-key"
            s.LLM_API_KEY = ""
            s.RERANKER_BASE_URL = ""
            s.RERANKER_MODEL = ""
            from app.services.reranker import get_reranker_provider, OpenAICompatibleRerankerProvider
            p = get_reranker_provider()
            assert isinstance(p, OpenAICompatibleRerankerProvider)

    def test_zhipu_no_key_raises(self):
        with patch("app.services.reranker.settings") as s:
            s.RERANKER_PROVIDER = "zhipu"
            s.RERANKER_API_KEY = ""
            s.LLM_API_KEY = ""
            from app.services.reranker import get_reranker_provider
            with pytest.raises(ValueError, match="RERANKER_API_KEY"):
                get_reranker_provider()

    def test_unsupported_raises(self):
        with patch("app.services.reranker.settings") as s:
            s.RERANKER_PROVIDER = "unknown_provider"
            from app.services.reranker import get_reranker_provider
            with pytest.raises(ValueError, match="Unsupported"):
                get_reranker_provider()


class TestEmailService:
    """B7: 邮件服务测试"""

    @pytest.mark.asyncio
    async def test_no_smtp_logs_only(self):
        """SMTP 未配置时应返回 True（降级为日志）"""
        with patch("app.services.email.settings") as s:
            s.SMTP_HOST = ""
            s.PROJECT_NAME = "Test"
            from app.services.email import send_reset_code_email
            result = await send_reset_code_email("test@example.com", "123456")
            assert result is True

    @pytest.mark.asyncio
    async def test_smtp_send_failure(self):
        """SMTP 连接失败应返回 False"""
        with patch("app.services.email.settings") as s, \
             patch("app.services.email.smtplib") as mock_smtp:
            s.SMTP_HOST = "smtp.test.com"
            s.SMTP_PORT = 465
            s.SMTP_TLS = False
            s.SMTP_USER = "user"
            s.SMTP_PASSWORD = "pass"
            s.SMTP_FROM = "noreply@test.com"
            s.PROJECT_NAME = "Test"
            mock_smtp.SMTP_SSL.side_effect = Exception("Connection failed")
            from app.services.email import send_reset_code_email
            result = await send_reset_code_email("test@example.com", "654321")
            assert result is False


class TestAuditService:
    """B8: 审计日志异步化测试"""

    @pytest.mark.asyncio
    async def test_sync_audit_adds_to_session(self):
        from app.services.audit import audit_action
        db = AsyncMock()
        db.add = MagicMock()
        await audit_action(
            db, user_id=1, org_id=2, action="test",
            resource_type="Test", tenant_id=100,
        )
        db.add.assert_called_once()
        log = db.add.call_args[0][0]
        assert log.action == "test"
        assert log.tenant_id == 100

    @pytest.mark.asyncio
    async def test_fire_audit_does_not_raise(self):
        """fire_audit 不应抛异常"""
        from app.services.audit import fire_audit
        # 在测试环境中可能没有运行中的事件循环用于 create_task
        # 但 fire_audit 应优雅降级
        fire_audit(
            user_id=1, org_id=2, action="test",
            resource_type="Test", tenant_id=100,
        )


class TestHealthAlert:
    """B9: 健康指标告警测试"""

    def test_normal_blood_pressure(self):
        """正常血压不应告警"""
        from app.services.health_alert import check_metric_alert
        alerts = check_metric_alert("blood_pressure", 120, 80)
        assert len(alerts) == 0

    def test_high_blood_pressure(self):
        """高血压应告警"""
        from app.services.health_alert import check_metric_alert
        alerts = check_metric_alert("blood_pressure", 160, 95)
        assert len(alerts) >= 1
        assert any("偏高" in a.message for a in alerts)

    def test_low_blood_sugar(self):
        """低血糖应告警"""
        from app.services.health_alert import check_metric_alert
        alerts = check_metric_alert("blood_sugar", 2.5)
        assert len(alerts) == 1
        assert alerts[0].level in ("warning", "danger")
        assert "偏低" in alerts[0].message

    def test_normal_heart_rate(self):
        from app.services.health_alert import check_metric_alert
        alerts = check_metric_alert("heart_rate", 72)
        assert len(alerts) == 0

    def test_high_heart_rate(self):
        from app.services.health_alert import check_metric_alert
        alerts = check_metric_alert("heart_rate", 130)
        assert len(alerts) == 1
        assert "偏高" in alerts[0].message

    def test_low_spo2_danger(self):
        """极低血氧应为 danger 级别"""
        from app.services.health_alert import check_metric_alert
        alerts = check_metric_alert("spo2", 70)
        assert len(alerts) == 1
        assert alerts[0].level == "danger"

    def test_unknown_metric_no_alert(self):
        """未知指标类型不应告警"""
        from app.services.health_alert import check_metric_alert
        alerts = check_metric_alert("unknown_type", 999)
        assert len(alerts) == 0

    def test_bmi_obese(self):
        from app.services.health_alert import check_metric_alert
        alerts = check_metric_alert("bmi", 32.0)
        assert len(alerts) == 1
        assert "偏高" in alerts[0].message


class TestConversationCompress:
    """B10: 对话压缩测试"""

    def test_should_not_compress_short(self):
        from app.services.conversation_compress import should_compress
        messages = [{"role": "user", "content": f"msg{i}"} for i in range(5)]
        assert should_compress(messages) is False

    def test_should_compress_long(self):
        from app.services.conversation_compress import should_compress
        messages = [{"role": "user", "content": f"msg{i}"} for i in range(15)]
        assert should_compress(messages) is True

    @pytest.mark.asyncio
    async def test_compress_reduces_count(self):
        from app.services.conversation_compress import compress_history

        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"消息{i}"}
            for i in range(15)
        ]

        async def fake_stream(prompt):
            yield "这是一段关于健康咨询的对话摘要"

        llm = MagicMock()
        llm.stream_text = fake_stream

        result = await compress_history(messages, llm)
        # 应该得到 1 条摘要 + 4 条最近消息 = 5
        assert len(result) == 5
        assert result[0]["role"] == "system"
        assert "摘要" in result[0]["content"]

    @pytest.mark.asyncio
    async def test_compress_fallback_on_error(self):
        from app.services.conversation_compress import compress_history

        messages = [{"role": "user", "content": f"消息{i}"} for i in range(15)]

        async def failing_stream(prompt):
            raise Exception("LLM error")
            yield  # noqa: unreachable

        llm = MagicMock()
        llm.stream_text = failing_stream

        result = await compress_history(messages, llm)
        assert len(result) == 4  # 降级为最近 4 条
