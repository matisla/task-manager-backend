import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """ """

    async def dispatch(self, request, call_next):
        """
        handle the request id from the header for logging purpose.
        """

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # ensure to start from zero
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )

        return response
