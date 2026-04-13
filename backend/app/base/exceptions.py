"""统一业务异常定义

Service 层抛出这些异常，main.py 的 exception_handler 统一转换为 HTTP 响应。
这样 Service 层不需要依赖 FastAPI 的 HTTPException。
"""


class BusinessError(Exception):
    """业务异常基类"""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(BusinessError):
    def __init__(self, resource: str = "Resource", id: int | str | None = None):
        msg = f"{resource} not found" + (f" (id={id})" if id else "")
        super().__init__(msg, code="NOT_FOUND")


class ForbiddenError(BusinessError):
    def __init__(self, message: str = "Not enough permissions"):
        super().__init__(message, code="FORBIDDEN")


class ConflictError(BusinessError):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, code="CONFLICT")


class QuotaExceededError(BusinessError):
    def __init__(self, message: str = "Quota exceeded"):
        super().__init__(message, code="QUOTA_EXCEEDED")


class ValidationError(BusinessError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, code="VALIDATION_ERROR")
