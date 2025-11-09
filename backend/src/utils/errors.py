"""Error handling utilities and custom exceptions."""
from typing import Any, Dict


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "INTERNAL_ERROR",
        details: Dict[str, Any] | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(APIError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found", details: Dict[str, Any] | None = None):
        super().__init__(message, 404, "NOT_FOUND", details)


class BadRequestError(APIError):
    """Invalid request."""

    def __init__(self, message: str = "Invalid request", details: Dict[str, Any] | None = None):
        super().__init__(message, 400, "BAD_REQUEST", details)


class UnauthorizedError(APIError):
    """Unauthorized access."""

    def __init__(self, message: str = "Unauthorized", details: Dict[str, Any] | None = None):
        super().__init__(message, 401, "UNAUTHORIZED", details)


class ForbiddenError(APIError):
    """Forbidden access."""

    def __init__(self, message: str = "Forbidden", details: Dict[str, Any] | None = None):
        super().__init__(message, 403, "FORBIDDEN", details)


class ConflictError(APIError):
    """Resource conflict."""

    def __init__(self, message: str = "Resource conflict", details: Dict[str, Any] | None = None):
        super().__init__(message, 409, "CONFLICT", details)


class RateLimitError(APIError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Too many requests", details: Dict[str, Any] | None = None):
        super().__init__(message, 429, "RATE_LIMIT_EXCEEDED", details)


def format_error_response(error: APIError) -> Dict[str, Any]:
    """Format error response."""
    return {
        "error": error.message,
        "code": error.code,
        "details": error.details
    }
