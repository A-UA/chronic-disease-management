from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any


class PluginRegistry:
    _factories: dict[str, dict[str, Callable]] = {}
    _instances: dict[str, dict[str, Any]] = {}
    _bootstrapped_categories: set[str] = set()

    @classmethod
    def register(cls, category: str, name: str, factory: Callable) -> None:
        cls._factories.setdefault(category, {})[name] = factory

    @classmethod
    def get(cls, category: str, name: str | None = None) -> Any:
        cls._bootstrap_category(category)
        key = name or cls._resolve_default(category)
        instances = cls._instances.setdefault(category, {})
        if key not in instances:
            factory = cls._factories[category][key]
            instances[key] = factory()
        return instances[key]

    @classmethod
    def list_plugins(cls, category: str) -> list[str]:
        cls._bootstrap_category(category)
        return list(cls._factories.get(category, {}).keys())

    @classmethod
    def _bootstrap_category(cls, category: str) -> None:
        if category in cls._bootstrapped_categories:
            return

        module_map = {
            "llm": "app.plugins.llm",
            "embedding": "app.plugins.embedding",
            "reranker": "app.plugins.reranker",
            "parser": "app.plugins.parser",
            "chunker": "app.plugins.chunker",
        }
        module_name = module_map.get(category)
        if module_name is not None:
            import_module(module_name)

        cls._bootstrapped_categories.add(category)

    @classmethod
    def _resolve_default(cls, category: str) -> str:
        from app.base.config import settings

        defaults = {
            "llm": "openai_compatible",
            "embedding": "openai_compatible",
            "reranker": settings.RERANKER_PROVIDER.lower().strip() or "noop",
            "parser": "pdf",
            "chunker": "medical_heading",
        }
        return defaults.get(category, "default")

    @classmethod
    def reset(cls) -> None:
        cls._instances.clear()
        cls._factories.clear()
        cls._bootstrapped_categories.clear()
