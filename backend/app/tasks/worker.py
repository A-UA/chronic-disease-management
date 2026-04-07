"""arq Worker 启动配置

启动命令：uv run arq app.tasks.worker.WorkerSettings
"""
import importlib
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _parse_redis_settings():
    """从 REDIS_URL 解析 arq RedisSettings"""
    from arq.connections import RedisSettings
    url = settings.REDIS_URL  # redis://localhost:6379/0
    # 简单解析，支持 redis://host:port/db 格式
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )


async def startup(ctx: dict):
    """Worker 启动时初始化"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s")
    # 触发插件注册（使用 importlib 避免变量名冲突）
    for plugin in ("llm", "embedding", "reranker", "parser", "chunker"):
        importlib.import_module(f"app.plugins.{plugin}")
    logger.info("arq Worker 已启动，已注册所有插件")


async def shutdown(ctx: dict):
    """Worker 关闭时清理"""
    logger.info("arq Worker 关闭")


class WorkerSettings:
    """arq Worker 配置"""
    redis_settings = _parse_redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = settings.ARQ_MAX_JOBS
    job_timeout = settings.ARQ_JOB_TIMEOUT

    # 注册异步任务
    functions = []

    @classmethod
    def collect_functions(cls):
        from app.modules.rag.tasks import process_document_task, write_audit_log_task
        cls.functions = [process_document_task, write_audit_log_task]
        return cls.functions


# 收集任务（模块加载时执行）
WorkerSettings.collect_functions()
