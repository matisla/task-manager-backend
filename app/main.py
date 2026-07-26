from contextlib import asynccontextmanager

import uvicorn
from auth.router import auth_router, user_router
from config import Environment, settings
from config.cors import set_cors
from config.database import ENGINE
from core.router import router as core_router
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context for live cycle of the app
    """

    yield

    if ENGINE is not None:
        ENGINE.dispose()


def create_app() -> FastAPI:
    """
    Create app instance for the application
    """

    fast_app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        docs_url="/docs" if settings.ENVIRONMENT == Environment.DEV else None,
        redoc_url="/redoc" if settings.ENVIRONMENT == Environment.DEV else None,
        lifespan=lifespan,
    )

    fast_app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    fast_app.include_router(user_router, prefix="/users", tags=["Users"])

    set_cors(fast_app)

    settings.log.configure()
    settings.db.set_engine(settings.DEBUG)

    return fast_app


if __name__ == "__main__":
    uvicorn.run("asgi:app", host="0.0.0.0", port=8000)
