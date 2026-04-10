"""OpenTelemetry 追踪工具 — 提供 trace_span 上下文管理器和 traced 装饰器

当 OpenTelemetry SDK 未安装或 OTLP 未配置时，所有追踪操作为无操作（noop），
不影响业务逻辑正常运行。
"""

from contextlib import contextmanager
from functools import wraps
from typing import Any

_tracer = None
_initialized = False


def _get_tracer():
    global _tracer, _initialized
    if not _initialized:
        _initialized = True
        try:
            from opentelemetry import trace

            _tracer = trace.get_tracer("cdm.backend")
        except ImportError:
            _tracer = None
    return _tracer


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None):
    """创建一个追踪 span 的上下文管理器

    当 OpenTelemetry 未安装时退化为 noop。
    """
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        yield span


def traced(name: str | None = None):
    """装饰器：自动为异步函数创建 span"""

    def decorator(func):
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        async def wrapper(*args, **kwargs):
            with trace_span(span_name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator
