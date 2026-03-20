from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.api import api_router
import traceback

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        err_msg = traceback.format_exc()
        print(err_msg)
        return JSONResponse(status_code=500, content={"detail": str(e), "traceback": err_msg})

# 挂载业务路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
