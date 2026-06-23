from fastapi import APIRouter
from app.routes.v1 import auth_routes, user_routes, motivation_routes, task_routes

router = APIRouter()
router.include_router(auth_routes.router)
router.include_router(user_routes.router)
router.include_router(motivation_routes.router)
router.include_router(task_routes.router)

