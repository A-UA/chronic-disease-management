"""向后兼容层：将旧 ProviderRegistry 委托到新 PluginRegistry

所有使用 `from app.plugins.provider_compat import registry` 的代码
无需修改即可正常工作。
"""
import app.plugins.embedding  # noqa: F401
import app.plugins.llm  # noqa: F401 — 触发插件注册
import app.plugins.reranker  # noqa: F401
from app.plugins.registry import PluginRegistry


class ProviderRegistry:
    """向后兼容层：所有调用委托到 PluginRegistry"""
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self):
        """兼容旧 initialize() 调用，新架构为延迟初始化，此处为 noop"""
        pass

    def get_llm(self):
        return PluginRegistry.get("llm")

    def get_embedding(self):
        return PluginRegistry.get("embedding")

    def get_reranker(self):
        return PluginRegistry.get("reranker")


registry = ProviderRegistry.get_instance()
