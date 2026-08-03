from fastapi import APIRouter
from sqlmodel import select

from app.db.deps import SessionDep

core_router = APIRouter(tags=["Core"])


@core_router.get("/")
async def homepage():
    """
    Endpoint compatible OpenAPI / Swagger UI.
    Basic root/greeting endpoint.

    Returns:
        dict: a greeting message.
    """

    return {"greeting": "Hello World !"}


@core_router.get("/health")
async def health(session: SessionDep):
    """
    Healthcheck endpoint: verifies the database is reachable.
    Mounted under /api, alongside the rest of the client-facing API.

    Args:
        session (Session): session used to access the database.

    Returns:
        dict: the health status.
    """

    await session.exec(select(1))

    return {"status": "ok"}
