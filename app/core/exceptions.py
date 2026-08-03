from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """
    Base class for business errors, translated to HTTP responses by a central handler.
    """

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        """
        Initialize the error, optionally overriding the class-level `detail`.

        Args:
            detail (str | None): message to use instead of the class default.
        """
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    """
    Raised when a requested resource does not exist.
    """

    status_code = 404
    detail = "Resource not found"


class ConflictError(AppError):
    """
    Raised when an operation conflicts with the resource's current state.
    """

    status_code = 409
    detail = "Conflict"


class BadRequestError(AppError):
    """
    Raised when the request is invalid on business grounds.
    """

    status_code = 400
    detail = "Bad request"


class UnauthorizedError(AppError):
    """
    Raised when authentication fails on business grounds.
    """

    status_code = 401
    detail = "Unauthorized"


async def app_error_handler(request: Request, exc: AppError):
    """
    Convert an AppError into a JSON error response.

    Args:
        request (Request): the incoming request (required by FastAPI's handler signature).
        exc (AppError): the business error being handled.

    Returns:
        JSONResponse: the HTTP response translated from `exc`.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "detail": exc.detail},
    )
