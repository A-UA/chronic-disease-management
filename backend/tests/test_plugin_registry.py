import pytest
from app.plugins.registry import PluginRegistry


def test_register_and_get():
    PluginRegistry.reset()
    PluginRegistry.register("test_cat", "impl_a", lambda: {"name": "a"})
    result = PluginRegistry.get("test_cat", "impl_a")
    assert result == {"name": "a"}
    PluginRegistry.reset()


def test_lazy_initialization():
    """工厂函数只在首次 get 时调用"""
    PluginRegistry.reset()
    call_count = {"n": 0}

    def factory():
        call_count["n"] += 1
        return "instance"

    PluginRegistry.register("lazy", "impl", factory)
    assert call_count["n"] == 0
    PluginRegistry.get("lazy", "impl")
    assert call_count["n"] == 1
    PluginRegistry.get("lazy", "impl")  # 第二次不再调用
    assert call_count["n"] == 1
    PluginRegistry.reset()


def test_get_unknown_raises():
    PluginRegistry.reset()
    with pytest.raises(KeyError):
        PluginRegistry.get("nonexistent", "x")
    PluginRegistry.reset()
