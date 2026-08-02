from config import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def set_cors(app: FastAPI):
    """
    Set up the CORS settings.

    Args:
        app (FastAPI): app to set up.
    """

    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
