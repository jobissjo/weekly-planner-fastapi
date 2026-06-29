from typing import List

from fastapi import APIRouter, Depends

from app.core.permissions import any_user_role, only_admin
from app.models.user import User
from app.schemas.common_schema import BaseResponse
from app.schemas.motivation_schema import (
    MotivationCreateSchema,
    MotivationResponse,
    MotivationUpdateSchema,
)
from app.services.motivation_service import MotivationService

router = APIRouter(tags=["Motivations"])
motivation_service = MotivationService()


@router.post("/admin/motivations", response_model=BaseResponse[MotivationResponse])
async def create_motivation(
    data: MotivationCreateSchema,
    admin_user: User = Depends(only_admin),
):
    motivation = await motivation_service.create_motivation(data)
    return BaseResponse(
        status="success",
        message="Motivation created successfully",
        data=MotivationResponse.model_validate(motivation),
    )


@router.get("/admin/motivations", response_model=BaseResponse[List[MotivationResponse]])
async def list_motivations(
    admin_user: User = Depends(only_admin),
):
    motivations = await motivation_service.list_all_motivations()
    data = [MotivationResponse.model_validate(m) for m in motivations]
    return BaseResponse(
        status="success",
        message="Motivations retrieved successfully",
        data=data,
    )


@router.get("/admin/motivations/{id}", response_model=BaseResponse[MotivationResponse])
async def get_motivation(
    id: str,
    admin_user: User = Depends(only_admin),
):
    motivation = await motivation_service.get_motivation_by_id(id)
    return BaseResponse(
        status="success",
        message="Motivation retrieved successfully",
        data=MotivationResponse.model_validate(motivation),
    )


@router.patch(
    "/admin/motivations/{id}", response_model=BaseResponse[MotivationResponse]
)
async def update_motivation(
    id: str,
    data: MotivationUpdateSchema,
    admin_user: User = Depends(only_admin),
):
    motivation = await motivation_service.update_motivation(id, data)
    return BaseResponse(
        status="success",
        message="Motivation updated successfully",
        data=MotivationResponse.model_validate(motivation),
    )


@router.delete("/admin/motivations/{id}", response_model=BaseResponse[None])
async def delete_motivation(
    id: str,
    admin_user: User = Depends(only_admin),
):
    await motivation_service.delete_motivation(id)
    return BaseResponse(
        status="success",
        message="Motivation deleted successfully",
        data=None,
    )


@router.get("/motivations/random", response_model=BaseResponse[MotivationResponse])
async def get_random_motivation(
    current_user: User = Depends(any_user_role),
):
    motivation = await motivation_service.get_random_active_motivation()
    return BaseResponse(
        status="success",
        message="Random active motivation retrieved successfully",
        data=MotivationResponse.model_validate(motivation),
    )
