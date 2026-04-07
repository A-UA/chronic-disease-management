from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    id: int
    kb_id: int
    org_id: int
    uploader_id: int
    patient_id: int | None
    file_name: str
    file_type: str
    file_size: int
    minio_url: str | None
    status: str
    failed_reason: str | None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
