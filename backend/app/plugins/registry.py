"""统一插件注册中心 — 配置驱动，延迟初始化"""
from typing import Any, Callable


class PluginRegistry:
    _factories: dict[str, dict[str, Callable]] = {}
    _instances: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(cls, category: str, name: str, factory: Callable) -> None:
        cls._factories.setdefault(category, {})[name] = factory

    @classmethod
    def get(cls, category: str, name: str | None = None) -> Any:
        key = name or cls._resolve_default(category)
        instances = cls._instances.setdefault(category, {})
        if key not in instances:
            factory = cls._factories[category][key]
            instances[key] = factory()
        return instances[key]

    @classmethod
    def list_plugins(cls, category: str) -> list[str]:
        return list(cls._factories.get(category, {}).keys())

    @classmethod
    def _resolve_default(cls, category: str) -> str:
        from app.core.config import settings
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
        """测试用：清除所有缓存实例和工厂注册"""
        cls._instances.clear()
        cls._factories.clear()
