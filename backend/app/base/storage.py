import logging
import re
import uuid
from pathlib import PurePosixPath

import aioboto3

from app.base.config import settings

logger = logging.getLogger(__name__)


def _sanitize_filename(filename: str) -> str:
    """安全化文件名：去除路径穿越字符，保留原始扩展名，使用 UUID 防止冲突"""
    # 提取纯文件名（去除任何路径部分）
    basename = PurePosixPath(filename).name
    # 去除危险字符，仅保留字母数字中文下划线点号横线
    safe_name = re.sub(r"[^\w\u4e00-\u9fff.\-]", "_", basename)
    # 用 UUID 前缀避免文件名冲突
    suffix = PurePosixPath(safe_name).suffix or ""
    return (
        f"{uuid.uuid4().hex[:12]}_{safe_name}"
        if safe_name
        else f"{uuid.uuid4().hex}{suffix}"
    )


class StorageService:
    """异步存储服务，避免 IO 阻塞"""

    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = settings.MINIO_URL
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket_name = settings.MINIO_BUCKET_NAME

    def _get_client(self):
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    async def upload_file(self, file_bytes: bytes, filename: str, org_id: str) -> str:
        safe_filename = _sanitize_filename(filename)
        object_name = f"{org_id}/{safe_filename}"
        async with self._get_client() as s3:
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file_bytes,
                )
                return f"{self.endpoint_url}/{self.bucket_name}/{object_name}"
            except Exception as e:
                logger.error(f"上传文件到 MinIO 失败: {str(e)}")
                raise

    async def delete_file(self, minio_url: str) -> bool:
        """根据 MinIO URL 删除对象存储中的文件"""
        try:
            # 从 URL 中提取 object_name: {endpoint}/{bucket}/{org_id}/{filename}
            prefix = f"{self.endpoint_url}/{self.bucket_name}/"
            if not minio_url.startswith(prefix):
                logger.warning(f"无法解析 MinIO URL: {minio_url}")
                return False
            object_name = minio_url[len(prefix) :]
            async with self._get_client() as s3:
                await s3.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                )
            logger.info(f"已从 MinIO 删除文件: {object_name}")
            return True
        except Exception as e:
            logger.error(f"从 MinIO 删除文件失败: {str(e)}")
            return False


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
