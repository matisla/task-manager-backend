import logging
from pathlib import Path

import uvicorn
from auth.router import auth_router, user_router
from config import Environment, load_settings
from config.cors import set_cors
from core.router import router as core_router
from fastapi import FastAPI
from tasks.router import router as tasks_router


def create_app(env_path: str | Path | None = None) -> FastAPI:
    """
    Create app instance for the application
    """

    settings = load_settings(env_path)
    logger = logging.getLogger(__name__)

    fast_app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        docs_url="/docs" if settings.ENVIRONMENT == Environment.DEV else None,
        redoc_url="/redoc" if settings.ENVIRONMENT == Environment.DEV else None,
    )

    fast_app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    fast_app.include_router(user_router, prefix="/users", tags=["Users"])
    fast_app.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
    fast_app.include_router(core_router, tags=["Core"])

    set_cors(fast_app)

    logger.debug("FastAPI ready")

    return fast_app


if __name__ == "__main__":
    uvicorn.run("asgi:app", host="0.0.0.0", port=8000)
