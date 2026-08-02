import logging
from pathlib import Path

import uvicorn
from auth.router import auth_router, user_router
from config import Environment, load_settings
from config.cors import set_cors
from core.exceptions import AppError
from core.router import core_router
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from tasks.router import tasks_router


def create_app(env_path: str | Path | None = None) -> FastAPI:
    """
    Create app instance for the application.

    Args:
        env_path (str | Path | None): if provided, load this specific env file,
            else use the default parameters.

    Returns:
        FastAPI: the configured application instance.
    """

    settings = load_settings(env_path)
    logger = logging.getLogger(__name__)

    fast_app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        docs_url="/docs" if settings.ENVIRONMENT != Environment.PROD else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != Environment.PROD else None,
    )

    fast_app.include_router(auth_router)
    fast_app.include_router(user_router)
    fast_app.include_router(tasks_router)
    fast_app.include_router(core_router)

    @fast_app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    set_cors(fast_app)

    logger.debug("FastAPI ready")

    return fast_app


if __name__ == "__main__":
    uvicorn.run("asgi:app", host="0.0.0.0", port=8000)
