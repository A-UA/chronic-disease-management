import uuid

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_URL,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        )
        self.bucket = settings.MINIO_BUCKET_NAME
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.s3_client.create_bucket(Bucket=self.bucket)

    def upload_file(self, file_bytes: bytes, filename: str, org_id: str) -> str:
        unique_filename = f"{org_id}/{uuid.uuid4()}_{filename}"
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=unique_filename,
            Body=file_bytes,
        )
        return f"{settings.MINIO_URL}/{self.bucket}/{unique_filename}"


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


def reset_storage_service():
    global _storage_service
    _storage_service = None
