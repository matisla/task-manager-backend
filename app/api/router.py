from fastapi.routing import APIRouter

from app.auth.router import auth_router, user_router
from app.core.router import core_router
from app.tasks.router import tasks_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(tasks_router)
api_router.include_router(core_router)
