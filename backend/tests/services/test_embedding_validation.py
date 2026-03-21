from unittest.mock import MagicMock

from app.services.embedding_validation import validate_embedding_provider


def test_validate_embedding_provider_reports_success():
    provider = MagicMock()
    provider.embed_query.return_value = [0.1, 0.2, 0.3]

    result = validate_embedding_provider(provider, sample_text="血糖高怎么办？")

    assert result["ok"] is True
    assert result["vector_length"] == 3
    assert result["error"] is None


def test_validate_embedding_provider_reports_failure():
    provider = MagicMock()
    provider.embed_query.side_effect = RuntimeError("unsupported endpoint")

    result = validate_embedding_provider(provider, sample_text="血糖高怎么办？")

    assert result["ok"] is False
    assert result["vector_length"] == 0
    assert "unsupported endpoint" in result["error"]
