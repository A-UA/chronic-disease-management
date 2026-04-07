"""统一业务异常定义"""
from fastapi import HTTPException


class NotFoundError(HTTPException):
    def __init__(self, resource: str = "Resource", detail: str | None = None):
        super().__init__(status_code=404, detail=detail or f"{resource} not found")


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=403, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=409, detail=detail)


class QuotaExceededError(HTTPException):
    def __init__(self, detail: str = "Quota exceeded"):
        super().__init__(status_code=429, detail=detail)
