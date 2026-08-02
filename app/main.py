from contextlib import asynccontextmanager

import uvicorn
from config import Environment, get_settings
from config.core import Settings
from core.exceptions import AppError, app_error_handler
from db.session import create_db_engine, create_session_factory
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import api_router


def create_app(settings: Settings | None = None) -> FastAPI:

    settings_: Settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):

        engine = create_db_engine(settings_.db.connexion_url)

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

    app.include_router(api_router, prefix="/api")

    @app.get("/health", tags=["infra"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("asgi:app", host="0.0.0.0", port=8000)
