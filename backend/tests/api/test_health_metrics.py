"""健康指标模块测试

覆盖：录入、列表、趋势、删除、更新、跨用户隔离
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import override_deps, MockScalarResult, TENANT_ID, ORG_ID, USER_ID


def _make_app():
    from app.api.endpoints.health_metrics import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/health-metrics")
    return app


def _patient(pid=4001, user_id=USER_ID, org_id=ORG_ID):
    p = MagicMock()
    p.id = pid
    p.user_id = user_id
    p.org_id = org_id
    p.tenant_id = TENANT_ID
    return p


def _metric(mid=7001, recorded_by=USER_ID, mtype="blood_pressure"):
    m = MagicMock()
    m.id = mid
    m.patient_id = 4001
    m.tenant_id = TENANT_ID
    m.org_id = ORG_ID
    m.recorded_by = recorded_by
    m.metric_type = mtype
    m.value = 130.0
    m.value_secondary = 85.0
    m.unit = "mmHg"
    m.measured_at = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    m.note = None
    m.created_at = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    return m


class TestCreateHealthMetric:
    @pytest.mark.asyncio
    async def test_create_blood_pressure(self):
        app = _make_app()
        patient = _patient()
        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[patient])
        db.refresh = AsyncMock()
        db.add = MagicMock()  # 非异步
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/health-metrics", json={
                "metric_type": "blood_pressure",
                "value": 130.0, "value_secondary": 85.0,
                "unit": "mmHg",
                "measured_at": "2026-04-01T08:00:00Z",
            })
        assert r.status_code == 200
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_blood_sugar(self):
        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[_patient()])
        db.refresh = AsyncMock()
        db.add = MagicMock()
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/health-metrics", json={
                "metric_type": "blood_sugar",
                "value": 6.5, "unit": "mmol/L",
                "measured_at": "2026-04-01T08:00:00Z",
                "note": "空腹",
            })
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_metric_type_422(self):
        app = _make_app()
        db = AsyncMock()
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/health-metrics", json={
                "metric_type": "invalid_type",
                "value": 100, "unit": "??",
                "measured_at": "2026-04-01T08:00:00Z",
            })
        assert r.status_code == 422


class TestListMyMetrics:
    @pytest.mark.asyncio
    async def test_list_ok(self):
        app = _make_app()
        patient = _patient()
        metrics = [_metric(), _metric(7002, mtype="blood_sugar")]
        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[patient]),
            MockScalarResult(items=metrics),
        ]
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/health-metrics/me")
        assert r.status_code == 200
        assert len(r.json()) == 2

    @pytest.mark.asyncio
    async def test_no_patient_404(self):
        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[])
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/health-metrics/me")
        assert r.status_code == 404


class TestGetTrend:
    @pytest.mark.asyncio
    async def test_trend_ok(self):
        app = _make_app()
        patient = _patient()
        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[patient]),
            MockScalarResult(items=[_metric(), _metric(7002)]),
        ]
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/health-metrics/me/trend?metric_type=blood_pressure")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestDeleteHealthMetric:
    @pytest.mark.asyncio
    async def test_delete_own(self):
        app = _make_app()
        metric = _metric()
        db = AsyncMock()
        db.get.return_value = metric
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.delete("/api/v1/health-metrics/7001")
        assert r.status_code == 200
        db.delete.assert_called_once_with(metric)

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        app = _make_app()
        db = AsyncMock()
        db.get.return_value = None
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.delete("/api/v1/health-metrics/99999")
        assert r.status_code == 404


class TestUpdateHealthMetric:
    @pytest.mark.asyncio
    async def test_update_own(self):
        app = _make_app()
        metric = _metric()
        db = AsyncMock()
        db.get.return_value = metric
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.put("/api/v1/health-metrics/7001", json={"value": 125.0})
        assert r.status_code == 200
        assert metric.value == 125.0

    @pytest.mark.asyncio
    async def test_update_others_403(self):
        app = _make_app()
        metric = _metric(recorded_by=9999)
        db = AsyncMock()
        db.get.return_value = metric
        override_deps(app, db=db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.put("/api/v1/health-metrics/7001", json={"value": 999.0})
        assert r.status_code == 403
