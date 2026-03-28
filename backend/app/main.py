import logging
import traceback
import orjson
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.api import api_router

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

class SnowflakeJSONResponse(ORJSONResponse):
    """
    自定义响应类：
    1. 使用 orjson 提供极致的性能
    2. 自动处理雪花 ID 等大整数，防止前端精度丢失
    """
    def render(self, content: Any) -> bytes:
        # 在序列化前执行转换
        content = bigint_to_str(content)
        return orjson.dumps(
            content,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
        )

# --- 应用初始化 ---

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    default_response_class=SnowflakeJSONResponse  # 设置为默认响应类，全项目生效
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Organization-ID"],
)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    """全局异常捕获中间件"""
    try:
        return await call_next(request)
    except Exception:
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500, content={"detail": "Internal Server Error"}
        )

# 挂载业务路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
