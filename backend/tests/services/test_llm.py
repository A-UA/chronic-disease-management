from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.llm import OpenAICompatibleLLMProvider, get_llm_provider


def test_get_llm_provider_returns_openai_compatible_provider(monkeypatch):
    monkeypatch.setattr("app.services.llm.settings.LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr("app.services.llm.settings.LLM_API_KEY", "secret")
    monkeypatch.setattr("app.services.llm.settings.LLM_BASE_URL", "https://api.xiaomimimo.com/v1")
    monkeypatch.setattr("app.services.llm.settings.CHAT_MODEL", "mimo-v2-flash")

    mock_client = MagicMock()
    mock_async_openai = MagicMock(return_value=mock_client)
    monkeypatch.setattr("app.services.llm.AsyncOpenAI", mock_async_openai)

    provider = get_llm_provider()

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    mock_async_openai.assert_called_once_with(
        api_key="secret",
        base_url="https://api.xiaomimimo.com/v1",
    )


@pytest.mark.asyncio
async def test_openai_compatible_llm_provider_streams_delta_text():
    chunk_one = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="结论"))],
    )
    chunk_two = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="：建议复查"))],
    )
    async def stream():
        yield chunk_one
        yield chunk_two

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=stream())

    provider = OpenAICompatibleLLMProvider(mock_client, model_name="mimo-v2-flash")

    parts = [part async for part in provider.stream_text("prompt-text")]

    assert parts == ["结论", "：建议复查"]
    mock_client.chat.completions.create.assert_awaited_once_with(
        model="mimo-v2-flash",
        messages=[{"role": "user", "content": "prompt-text"}],
        stream=True,
    )


@pytest.mark.asyncio
async def test_openai_compatible_llm_provider_completes_text():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))],
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=response)

    provider = OpenAICompatibleLLMProvider(mock_client, model_name="mimo-v2-flash")
    text = await provider.complete_text("prompt-text")

    assert text == '{"ok":true}'
    mock_client.chat.completions.create.assert_awaited_once_with(
        model="mimo-v2-flash",
        messages=[{"role": "user", "content": "prompt-text"}],
        stream=False,
    )


def test_get_llm_provider_requires_api_key_for_openai_compatible(monkeypatch):
    monkeypatch.setattr("app.services.llm.settings.LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr("app.services.llm.settings.LLM_API_KEY", "")
    monkeypatch.setattr("app.services.llm.settings.LLM_BASE_URL", "https://api.xiaomimimo.com/v1")

    with pytest.raises(ValueError, match="LLM_API_KEY is required"):
        get_llm_provider()


def test_get_llm_provider_requires_base_url_for_openai_compatible(monkeypatch):
    monkeypatch.setattr("app.services.llm.settings.LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr("app.services.llm.settings.LLM_API_KEY", "secret")
    monkeypatch.setattr("app.services.llm.settings.LLM_BASE_URL", "")

    with pytest.raises(ValueError, match="LLM_BASE_URL is required"):
        get_llm_provider()