from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_knowledge_parse_upload(mocker):
    # Mock the ingestion process
    mocker.patch("app.routers.internal.process_document_to_milvus", return_value=3)
    
    response = client.post(
        "/internal/knowledge/parse",
        data={"kb_id": "kb_test_01"},
        files={"file": ("sample.txt", b"Hello knowledge", "text/plain")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["chunk_count"] == 3
    assert data["filename"] == "sample.txt"
