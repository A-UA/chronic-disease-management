import logging
import traceback
from typing import Any

import orjson
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.base.config import settings
from app.routers import api_router
from app.services.rag.provider_service import provider_service

logger = logging.getLogger(__name__)

# --- 顶级架构：大整数安全序列化逻辑 ---

JS_MAX_INT = 9007199254740991
JS_MIN_INT = -9007199254740991


def bigint_to_str(obj: Any) -> Any:
    """递归将超过 JS 精度范围的 int 转换为 str"""
    if isinstance(obj, int) and (obj > JS_MAX_INT or obj < JS_MIN_INT):
        return str(obj)
    if isinstance(obj, dict):
        return {k: bigint_to_str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [bigint_to_str(v) for v in obj]
    return obj


class SnowflakeJSONResponse(JSONResponse):
    """
    自定义响应类：
    1. 使用 orjson 提供极致的性能
    2. 自动处理雪花 ID 等大整数，防止前端精度丢失
    """

    def render(self, content: Any) -> bytes:
        # 在序列化前执行转换
        content = bigint_to_str(content)
        return orjson.dumps(
            content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
        )


# --- 应用初始化 ---

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    default_response_class=SnowflakeJSONResponse,
)

# --- 可观测性初始化 ---
from app.telemetry.setup import setup_telemetry

setup_telemetry(app)

# --- 插件注册（触发所有插件的延迟注册） ---
import importlib as _importlib

for _plugin in ("llm", "embedding", "reranker", "parser", "chunker"):
    _importlib.import_module(f"app.plugins.{_plugin}")

provider_service.validate_runtime_dependencies()


# ── 业务异常处理器 ──
from app.base.exceptions import BusinessError


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    """Service 层 BusinessError → HTTP 响应"""
    status_map = {
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "FORBIDDEN": 403,
        "QUOTA_EXCEEDED": 402,
        "VALIDATION_ERROR": 422,
        "BUSINESS_ERROR": 400,
    }
    return SnowflakeJSONResponse(
        status_code=status_map.get(exc.code, 400),
        content={"detail": exc.message, "code": exc.code},
    )


# 注册异常处理器以保护大整数精度
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    response = await http_exception_handler(request, exc)
    # 将标准 JSONResponse 内容提取并重新用 SnowflakeJSONResponse 封装
    return SnowflakeJSONResponse(
        status_code=response.status_code,
        content=bigint_to_str(orjson.loads(response.body)),
        headers=dict(response.headers),
    )


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    response = await request_validation_exception_handler(request, exc)
    return SnowflakeJSONResponse(
        status_code=response.status_code,
        content=bigint_to_str(orjson.loads(response.body)),
        headers=dict(response.headers),
    )


# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# 请求追踪中间件
from app.base.middleware import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    """全局异常捕获中间件"""
    try:
        return await call_next(request)
    except Exception:
        logger.error(traceback.format_exc())
        return SnowflakeJSONResponse(
            status_code=500, content={"detail": "Internal Server Error"}
        )


# 挂载业务路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    """增强版健康检查：检测 Redis、PostgreSQL 等核心依赖的可达性"""
    from sqlalchemy import text

    from app.base.database import AsyncSessionLocal
    from app.services.system.quota import get_redis_client

    checks = {"status": "ok", "redis": "ok", "database": "ok"}

    # 检查 Redis
    try:
        redis = get_redis_client()
        await redis.ping()
    except Exception as e:
        checks["redis"] = f"error: {type(e).__name__}"
        checks["status"] = "degraded"

    # 检查 PostgreSQL
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"
        checks["status"] = "unhealthy"

    status_code = 200 if checks["status"] == "ok" else 503
    return SnowflakeJSONResponse(content=checks, status_code=status_code)
