from database import SessionDep
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def homepage(session: SessionDep):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    """

    return str({"greeting": "Hello World !"})
