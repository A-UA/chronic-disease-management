from unittest.mock import MagicMock, patch

from app.services.storage import StorageService

def test_upload_file():
    mock_s3 = MagicMock()
    mock_s3.head_bucket.return_value = {}

    with patch("app.services.storage.boto3.client", return_value=mock_s3):
        service = StorageService()

        file_content = b"dummy content"
        url = service.upload_file(file_content, "test.pdf", "org123")

    mock_s3.put_object.assert_called_once()
    assert "org123/" in url
    assert "test.pdf" in url

