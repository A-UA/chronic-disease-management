"""主应用入口测试"""
import pytest
from unittest.mock import patch


class TestAppCreation:
    def test_import_app(self):
        from app.main import app
        assert app is not None

    def test_app_has_routes(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert len(routes) > 0

    def test_docs_endpoint(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert "/docs" in routes or "/openapi.json" in routes
