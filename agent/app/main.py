"""Agent AI 中间层 — FastAPI 入口"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.internal import router as internal_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CDM Agent - AI Middleware",
    description="Python AI middleware for Chronic Disease Management. Internal APIs only.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Initializing CDM Agent AI Middleware...")
    from app.vectorstore.milvus import MilvusVectorStore

    try:
        store = MilvusVectorStore(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            collection_prefix=settings.MILVUS_COLLECTION_PREFIX,
        )
        await store.ensure_collection(
            "kb", dimension=1536
        )  # temp dimension for startup check
    except Exception as e:
        logger.warning(
            f"Failed to connect to Milvus at startup (might not be ready): {e}"
        )


app.include_router(internal_router)
