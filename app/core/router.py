from database import SessionDep
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def homepage(session: SessionDep):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    Basic healthcheck / greeting endpoint.

    Args:
        session (Session): session used to access the database.

    Returns:
        str: a greeting message.
    """

    return str({"greeting": "Hello World !"})
