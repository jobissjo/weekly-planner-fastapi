from typing import List
from fastapi import APIRouter, Depends, Query
from app.core.permissions import only_admin, any_user_role
from app.models.user import User
from app.schemas.common_schema import BaseResponse
from app.schemas.streak_schema import (
    StreakRuleCreateSchema,
    StreakRuleUpdateSchema,
    StreakRuleResponse,
    UserStreakResponse,
)
from app.services.streak_service import StreakService

router = APIRouter(tags=["Streaks"])
streak_service = StreakService()


# --- Admin StreakRule CRUD Endpoints ---

@router.post("/admin/streak-rules", response_model=BaseResponse[StreakRuleResponse])
async def create_streak_rule(
    data: StreakRuleCreateSchema,
    admin_user: User = Depends(only_admin),
):
    rule = await streak_service.create_streak_rule(data)
    return BaseResponse(
        status="success",
        message="Streak rule created successfully",
        data=StreakRuleResponse.model_validate(rule),
    )


@router.get("/admin/streak-rules", response_model=BaseResponse[List[StreakRuleResponse]])
async def list_streak_rules(
    admin_user: User = Depends(only_admin),
):
    rules = await streak_service.list_all_streak_rules()
    return BaseResponse(
        status="success",
        message="Streak rules retrieved successfully",
        data=[StreakRuleResponse.model_validate(r) for r in rules],
    )


@router.get("/admin/streak-rules/{id}", response_model=BaseResponse[StreakRuleResponse])
async def get_streak_rule(
    id: str,
    admin_user: User = Depends(only_admin),
):
    rule = await streak_service.get_streak_rule_by_id(id)
    return BaseResponse(
        status="success",
        message="Streak rule retrieved successfully",
        data=StreakRuleResponse.model_validate(rule),
    )


@router.patch("/admin/streak-rules/{id}", response_model=BaseResponse[StreakRuleResponse])
async def update_streak_rule(
    id: str,
    data: StreakRuleUpdateSchema,
    admin_user: User = Depends(only_admin),
):
    rule = await streak_service.update_streak_rule(id, data)
    return BaseResponse(
        status="success",
        message="Streak rule updated successfully",
        data=StreakRuleResponse.model_validate(rule),
    )


@router.delete("/admin/streak-rules/{id}", response_model=BaseResponse[None])
async def delete_streak_rule(
    id: str,
    admin_user: User = Depends(only_admin),
):
    await streak_service.delete_streak_rule(id)
    return BaseResponse(
        status="success",
        message="Streak rule deleted successfully",
        data=None,
    )


# --- User Streak Endpoints ---

@router.get("/user/streak", response_model=BaseResponse[UserStreakResponse])
async def get_user_streak(
    today: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: User = Depends(any_user_role),
):
    user_streak = await streak_service.get_or_update_user_streak(current_user.id, today)
    return BaseResponse(
        status="success",
        message="User streak retrieved successfully",
        data=UserStreakResponse.model_validate(user_streak),
    )
