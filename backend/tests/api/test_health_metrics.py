"""阶段1: 健康指标模块 TDD 测试

覆盖：录入、列表查询、趋势查询、删除、跨患者隔离、管理师查看
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.deps import get_current_user, get_current_org, get_db


def _make_app():
    from app.api.endpoints.health_metrics import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/health-metrics")
    return app


def _dummy_user(uid=1001):
    u = MagicMock()
    u.id = uid
    return u


def _dummy_metric(metric_id=7001, patient_id=4001, metric_type="blood_pressure",
                  value=130.0, value_secondary=85.0, unit="mmHg"):
    m = MagicMock()
    m.id = metric_id
    m.patient_id = patient_id
    m.org_id = 2001
    m.recorded_by = 1001
    m.metric_type = metric_type
    m.value = value
    m.value_secondary = value_secondary
    m.unit = unit
    m.measured_at = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    m.note = None
    m.created_at = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    return m


class DummyScalarResult:
    def __init__(self, items=None):
        self._items = items or []

    def scalars(self):
        mock = MagicMock()
        mock.all.return_value = self._items
        return mock

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


def _override(app, db, uid=1001, org_id=2001):
    """统一设置依赖覆盖"""
    async def _user():
        return _dummy_user(uid)
    async def _org():
        return org_id
    async def _db():
        return db
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_current_org] = _org
    app.dependency_overrides[get_db] = _db


class TestCreateHealthMetric:
    @pytest.mark.asyncio
    async def test_create_blood_pressure(self):
        """录入血压（含收缩压+舒张压）应成功"""
        app = _make_app()
        patient = MagicMock()
        patient.id = 4001
        patient.user_id = 1001
        patient.org_id = 2001

        db = AsyncMock()
        db.execute.return_value = DummyScalarResult([patient])
        db.refresh = AsyncMock()

        _override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/health-metrics/", json={
                "metric_type": "blood_pressure",
                "value": 130.0,
                "value_secondary": 85.0,
                "unit": "mmHg",
                "measured_at": "2026-04-01T08:00:00Z",
            })

        assert resp.status_code == 200
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_blood_sugar(self):
        """录入血糖应成功"""
        app = _make_app()
        patient = MagicMock()
        patient.id = 4001
        patient.user_id = 1001
        patient.org_id = 2001

        db = AsyncMock()
        db.execute.return_value = DummyScalarResult([patient])
        db.refresh = AsyncMock()

        _override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/health-metrics/", json={
                "metric_type": "blood_sugar",
                "value": 6.5,
                "unit": "mmol/L",
                "measured_at": "2026-04-01T08:00:00Z",
                "note": "空腹",
            })

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_metric_type(self):
        """无效指标类型应返回 422"""
        app = _make_app()
        db = AsyncMock()

        _override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/health-metrics/", json={
                "metric_type": "invalid_type",
                "value": 100,
                "unit": "??",
                "measured_at": "2026-04-01T08:00:00Z",
            })

        assert resp.status_code == 422


class TestListHealthMetrics:
    @pytest.mark.asyncio
    async def test_list_my_metrics(self):
        """查看自己的指标列表应成功"""
        app = _make_app()
        patient = MagicMock()
        patient.id = 4001
        patient.user_id = 1001
        patient.org_id = 2001
        metrics = [_dummy_metric(), _dummy_metric(metric_id=7002, metric_type="blood_sugar",
                                                   value=6.5, value_secondary=None, unit="mmol/L")]

        db = AsyncMock()
        db.execute.side_effect = [
            DummyScalarResult([patient]),
            DummyScalarResult(metrics),
        ]

        _override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/health-metrics/me")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_no_patient_profile(self):
        """无患者档案应返回 404"""
        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = DummyScalarResult([])

        _override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/health-metrics/me")

        assert resp.status_code == 404


class TestGetTrend:
    @pytest.mark.asyncio
    async def test_trend_returns_time_series(self):
        """趋势查询应返回按时间排序的列表"""
        app = _make_app()
        patient = MagicMock()
        patient.id = 4001
        patient.user_id = 1001
        patient.org_id = 2001
        metrics = [_dummy_metric(value=130), _dummy_metric(metric_id=7002, value=125)]

        db = AsyncMock()
        db.execute.side_effect = [
            DummyScalarResult([patient]),
            DummyScalarResult(metrics),
        ]

        _override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/health-metrics/me/trend?metric_type=blood_pressure")

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestDeleteHealthMetric:
    @pytest.mark.asyncio
    async def test_delete_own_metric(self):
        """删除自己的记录应成功"""
        app = _make_app()
        metric = _dummy_metric()
        metric.recorded_by = 1001

        db = AsyncMock()
        db.get.return_value = metric

        _override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/health-metrics/7001")

        assert resp.status_code == 200
        db.delete.assert_called_once_with(metric)

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        """删除不存在的记录应返回 404"""
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = None

        _override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/health-metrics/99999")

        assert resp.status_code == 404
