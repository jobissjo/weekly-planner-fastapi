from typing import List
from fastapi import APIRouter, Depends
from app.core.permissions import any_user_role
from app.models.user import User
from app.schemas.common_schema import BaseResponse
from app.schemas.reward_schema import RewardCreateSchema, RewardResponse
from app.services.reward_service import RewardService

router = APIRouter(prefix="/rewards", tags=["Rewards"])
reward_service = RewardService()


@router.get("", response_model=BaseResponse[List[RewardResponse]])
async def list_rewards(
    current_user: User = Depends(any_user_role),
):
    rewards = await reward_service.list_rewards(current_user.id)
    return BaseResponse(
        status="success",
        message="Rewards retrieved successfully",
        data=[RewardResponse.model_validate(r) for r in rewards],
    )


@router.post("", response_model=BaseResponse[RewardResponse])
async def create_reward(
    data: RewardCreateSchema,
    current_user: User = Depends(any_user_role),
):
    reward = await reward_service.create_reward(
        current_user.id, data.title, data.description
    )
    return BaseResponse(
        status="success",
        message="Reward created successfully",
        data=RewardResponse.model_validate(reward),
    )


@router.post("/{id}/select", response_model=BaseResponse[RewardResponse])
async def select_favorite_reward(
    id: str,
    current_user: User = Depends(any_user_role),
):
    reward = await reward_service.select_favorite_reward(current_user.id, id)
    return BaseResponse(
        status="success",
        message="Favorite reward selected successfully",
        data=RewardResponse.model_validate(reward),
    )


@router.delete("/{id}", response_model=BaseResponse[None])
async def delete_reward(
    id: str,
    current_user: User = Depends(any_user_role),
):
    await reward_service.delete_reward(current_user.id, id)
    return BaseResponse(
        status="success",
        message="Reward deleted successfully",
        data=None,
    )
