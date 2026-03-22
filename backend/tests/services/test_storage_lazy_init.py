from unittest.mock import MagicMock, patch

from app.services.storage import get_storage_service

def test_get_storage_service_initializes_once_and_is_lazy():
    with patch("app.services.storage.aioboto3.Session"):
        service_a = get_storage_service()
        service_b = get_storage_service()

    assert service_a is service_b
