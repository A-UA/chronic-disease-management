import asyncio
from app.telemetry.tracing import trace_span, traced


def test_trace_span_context_manager():
    """trace_span 上下文管理器不抛异常（OTel 未安装时为 noop）"""
    with trace_span("test.span", attributes={"key": "value"}):
        result = 1 + 1
    assert result == 2


def test_traced_decorator():
    """traced 装饰器正常包装异步函数"""
    @traced("test.func")
    async def my_func(x: int) -> int:
        return x * 2

    result = asyncio.run(my_func(5))
    assert result == 10


def test_trace_span_without_attributes():
    """trace_span 不传 attributes 也正常运行"""
    with trace_span("test.no_attr") as span:
        value = "hello"
    assert value == "hello"
