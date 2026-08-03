from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Environment, Settings, get_settings
from app.core.exceptions import AppError, app_error_handler
from app.core.middlewares import RequestContextMiddleware
from app.db.session import create_db_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Build and configure the FastAPI application.

    Args:
        settings (Settings | None): settings to use; defaults to `get_settings()`.

    Returns:
        FastAPI: the configured application.
    """

    settings_: Settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """
        Open the database engine on startup and dispose of it on shutdown.
        """

        engine = create_db_engine(
            settings_.db.connexion_url,
            settings_.db.ECHO,
        )

        # fail-fast check for database connexion
        async with engine.connect():
            pass

        # aquire a session to generate a ping to database
        app.state.session_factory = create_session_factory(engine)

        yield

        # close connexion with the database
        await engine.dispose()

    app = FastAPI(
        title=settings_.PROJECT_NAME,
        debug=settings_.DEBUG,
        docs_url="/docs" if settings_.ENVIRONMENT != Environment.PROD else None,
        redoc_url="/redoc" if settings_.ENVIRONMENT != Environment.PROD else None,
        lifespan=lifespan,
    )

    app.add_exception_handler(AppError, app_error_handler)

    app.add_middleware(CORSMiddleware, **settings_.cors.allows)
    app.add_middleware(RequestContextMiddleware)

    app.include_router(api_router, prefix="/api")

    @app.get("/health", tags=["infra"])
    async def health():
        """
        Liveness check, without touching the database. Not versioned, not part of the
        client-facing API contract (used by the Docker healthcheck).
        """
        return {"status": "ok"}

    return app
