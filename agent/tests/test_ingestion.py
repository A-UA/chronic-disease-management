from app.agent.ingestion import process_document_to_milvus

def test_process_document_to_milvus(mocker):
    # Mock OpenAiEmbeddings and Milvus to avoid real network calls
    mocker.patch("app.agent.ingestion.OpenAIEmbeddings")
    mock_milvus = mocker.patch("app.agent.ingestion.Milvus")
    
    # Mock the add_documents instance method
    mock_instance = mock_milvus.return_value
    mock_instance.add_documents.return_value = ["id1", "id2"]
    
    file_bytes = "Test line 1.\nTest line 2.".encode("utf-8")
    chunk_count = process_document_to_milvus(file_bytes, "test.txt", "kb_123")
    
    assert chunk_count > 0
    mock_instance.add_documents.assert_called_once()
