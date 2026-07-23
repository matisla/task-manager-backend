import uvicorn

from contextlib import asynccontextmanager

from fastapi import FastAPI

from auth.router import auth_router, user_router

from config import settings, Environment
from config.database import set_engine, ENGINE
from config.cors import set_cors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context for live cycle of the app
    """

    set_engine(settings.db.connexion_url)

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
    set_engine(settings.db.connexion_url)

    print("hello")

    return fast_app


if __name__ == "__main__":
    uvicorn.run("asgi:app", host="0.0.0.0", port=8000)
