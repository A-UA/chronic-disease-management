import sys
from unittest.mock import patch, MagicMock

# Mock boto3 before importing app modules that instantiate it
mock_boto = MagicMock()
mock_s3 = MagicMock()
mock_boto.client.return_value = mock_s3

with patch.dict(sys.modules, {'boto3': mock_boto}):
    from app.services.storage import StorageService

def test_upload_file():
    # Initialize service
    service = StorageService()
    
    # Test upload
    file_content = b"dummy content"
    url = service.upload_file(file_content, "test.pdf", "org123")
    
    # Verify s3 client was called
    mock_s3.put_object.assert_called_once()
    assert "org123/" in url
    assert "test.pdf" in url

