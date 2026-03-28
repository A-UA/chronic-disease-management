import logging
import json
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api import api_router
import traceback
from typing import Any

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


# Global JSON serializer to handle large integers for JavaScript compatibility
def serialize_large_int(obj: Any) -> Any:
    if isinstance(obj, int) and (obj > 9007199254740991 or obj < -9007199254740991):
        return str(obj)
    if isinstance(obj, dict):
        return {k: serialize_large_int(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_large_int(v) for v in obj]
    return obj


@app.middleware("http")
async def handle_large_int_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # We only care about JSON responses
    if response.headers.get("content-type") == "application/json":
        # Buffer the entire response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
            
        try:
            data = json.loads(body)
            # Recursively convert large integers to strings
            processed_data = serialize_large_int(data)
            new_body = json.dumps(processed_data).encode("utf-8")
            
            # Create a new response with the modified body
            return Response(
                content=new_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json"
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            # If it's not valid JSON, return the original response
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Organization-ID"],
)


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
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
