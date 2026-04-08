from __future__ import annotations

from pathlib import Path
from typing import Any

from app.plugins.registry import PluginRegistry


class ProviderResolutionError(RuntimeError):
    """Raised when a runtime provider cannot be resolved."""


class ProviderService:
    _PARSER_BY_SUFFIX = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".txt": "text",
    }

    def get_llm(self) -> Any:
        return self._get("llm")

    def get_embedding(self) -> Any:
        return self._get("embedding")

    def get_reranker(self) -> Any:
        return self._get("reranker")

    def get_chunker(self) -> Any:
        return self._get("chunker")

    def get_parser(self, name: str) -> Any:
        return self._get("parser", name)

    def get_parser_for_filename(self, filename: str) -> Any:
        suffix = Path(filename).suffix.lower()
        parser_name = self._PARSER_BY_SUFFIX.get(suffix)
        if parser_name is None:
            raise ProviderResolutionError(f"Unsupported parser suffix: {suffix or 'unknown'}")
        return self.get_parser(parser_name)

    def _get(self, category: str, name: str | None = None) -> Any:
        try:
            return PluginRegistry.get(category, name)
        except Exception as exc:  # pragma: no cover - exercised by tests via monkeypatch
            label = f"{category}:{name}" if name is not None else category
            raise ProviderResolutionError(f"Failed to resolve provider: {label}") from exc


provider_service = ProviderService()
