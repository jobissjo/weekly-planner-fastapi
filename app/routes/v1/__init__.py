from fastapi import APIRouter

from app.routes.v1 import (
    announcement_routes,
    auth_routes,
    chatbot_routes,
    feedback_routes,
    gmail_routes,
    habit_quitter_routes,
    motivation_routes,
    reward_routes,
    streak_routes,
    task_routes,
    user_routes,
)

router = APIRouter()
router.include_router(auth_routes.router)
router.include_router(user_routes.router)
router.include_router(motivation_routes.router)
router.include_router(task_routes.router)
router.include_router(streak_routes.router)
router.include_router(reward_routes.router)
router.include_router(chatbot_routes.router)
router.include_router(feedback_routes.router)
router.include_router(announcement_routes.router)
router.include_router(habit_quitter_routes.router)
router.include_router(gmail_routes.router)
