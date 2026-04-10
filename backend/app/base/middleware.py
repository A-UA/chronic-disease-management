"""请求追踪中间件：为每个请求注入 X-Request-ID"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# 当前请求 ID 的上下文变量，可在日志 filter 中使用
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求生成或透传 X-Request-ID，并注入响应头和日志上下文"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 优先使用客户端传入的 ID，否则自动生成
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request_id_ctx.set(rid)

        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response
