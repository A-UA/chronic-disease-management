"""通用响应 DTO"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PagedResponse(BaseModel, Generic[T]):
    """统一分页响应格式"""

    items: list[T]
    total: int
    skip: int
    limit: int


class StatusResponse(BaseModel):
    """统一状态响应"""

    status: str = "ok"
    message: str | None = None
