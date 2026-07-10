from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code


class AuthenticationError(AppException):
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class GuardrailViolationError(AppException):
    """Raised when input or output fails a guardrail check."""

    def __init__(self, message: str, violations: list[str] | None = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.violations = violations or []


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    body = {"error": exc.message}
    if isinstance(exc, GuardrailViolationError):
        body["violations"] = exc.violations
    return JSONResponse(status_code=exc.status_code, content=body)
