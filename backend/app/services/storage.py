import asyncio
import logging
from io import BytesIO
from typing import Optional

import aioboto3
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """异步存储服务，避免 IO 阻塞"""
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = settings.MINIO_URL
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket_name = settings.MINIO_BUCKET_NAME

    async def upload_file(self, file_bytes: bytes, filename: str, org_id: str) -> str:
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as s3:
            object_name = f"{org_id}/{filename}"
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file_bytes,
                )
                # 构造并返回持久化访问链接（根据实际 MinIO 路径策略）
                return f"{self.endpoint_url}/{self.bucket_name}/{object_name}"
            except Exception as e:
                logger.error(f"Failed to upload to MinIO: {str(e)}")
                raise

_storage_service: Optional[StorageService] = None

def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
