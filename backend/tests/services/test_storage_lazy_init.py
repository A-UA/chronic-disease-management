from unittest.mock import MagicMock, patch

from app.services.storage import get_storage_service, reset_storage_service


def test_get_storage_service_initializes_once_and_is_lazy():
    mock_s3 = MagicMock()
    mock_s3.head_bucket.return_value = {}

    reset_storage_service()
    with patch("app.services.storage.boto3.client", return_value=mock_s3) as client_factory:
        service_a = get_storage_service()
        service_b = get_storage_service()

    assert service_a is service_b
    client_factory.assert_called_once()
