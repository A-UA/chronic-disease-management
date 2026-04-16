import os
from app.config import settings

def test_settings_load():
    os.environ["MILVUS_HOST"] = "test-host"
    os.environ["GATEWAY_URL"] = "http://localhost:8080"
    
    assert settings.model_dump() is not None
    assert "MILVUS_HOST" in settings.model_fields
