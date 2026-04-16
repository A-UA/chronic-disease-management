from __future__ import annotations

import pytest

from app.plugins.registry import PluginRegistry


def test_provider_service_returns_registered_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.rag.provider_service import provider_service

    sentinels = {
        ("llm", None): object(),
        ("embedding", None): object(),
        ("reranker", None): object(),
        ("chunker", None): object(),
        ("parser", "pdf"): object(),
        ("parser", "docx"): object(),
        ("parser", "text"): object(),
    }

    def fake_get(category: str, name: str | None = None):
        return sentinels[(category, name)]

    monkeypatch.setattr(PluginRegistry, "get", fake_get)

    assert provider_service.get_llm() is sentinels[("llm", None)]
    assert provider_service.get_embedding() is sentinels[("embedding", None)]
    assert provider_service.get_reranker() is sentinels[("reranker", None)]
    assert provider_service.get_chunker() is sentinels[("chunker", None)]
    assert (
        provider_service.get_parser_for_filename("report.pdf")
        is sentinels[("parser", "pdf")]
    )
    assert (
        provider_service.get_parser_for_filename("report.docx")
        is sentinels[("parser", "docx")]
    )
    assert (
        provider_service.get_parser_for_filename("report.txt")
        is sentinels[("parser", "text")]
    )


def test_provider_service_normalizes_registry_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.rag.provider_service import (
        ProviderResolutionError,
        provider_service,
    )

    def fake_get(category: str, name: str | None = None):
        raise KeyError(f"{category}:{name}")

    monkeypatch.setattr(PluginRegistry, "get", fake_get)

    with pytest.raises(ProviderResolutionError):
        provider_service.get_llm()


def test_provider_service_rejects_unsupported_parser_suffix() -> None:
    from app.services.rag.provider_service import (
        ProviderResolutionError,
        provider_service,
    )

    with pytest.raises(ProviderResolutionError):
        provider_service.get_parser_for_filename("report.xlsx")


def test_provider_service_validates_runtime_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.rag.provider_service import provider_service

    calls: list[str] = []

    monkeypatch.setattr(
        provider_service,
        "get_llm",
        lambda: calls.append("llm") or object(),
    )
    monkeypatch.setattr(
        provider_service,
        "get_embedding",
        lambda: calls.append("embedding") or object(),
    )
    monkeypatch.setattr(
        provider_service,
        "get_reranker",
        lambda: calls.append("reranker") or object(),
    )
    monkeypatch.setattr(
        provider_service,
        "get_chunker",
        lambda: calls.append("chunker") or object(),
    )
    monkeypatch.setattr(
        provider_service,
        "get_parser_for_filename",
        lambda filename: calls.append(f"parser:{filename}") or object(),
    )

    provider_service.validate_runtime_dependencies()

    assert calls == [
        "llm",
        "embedding",
        "reranker",
        "chunker",
        "parser:bootstrap.pdf",
    ]
