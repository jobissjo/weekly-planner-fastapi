from typing import List

from fastapi import APIRouter, Depends

from app.core.permissions import any_user_role, only_admin
from app.models import User
from app.models.feedback import Feedback
from app.schemas.common_schema import BaseResponse
from app.schemas.feedback_schema import (
    FeedbackCreateSchema,
    FeedbackResponse,
    FeedbackUpdateStatusSchema,
)
from app.utils.common import CustomException

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=BaseResponse[FeedbackResponse])
async def create_feedback(
    data: FeedbackCreateSchema,
    current_user: User = Depends(any_user_role),
):
    """
    Submit feedback, a report, a suggestion, or contact the admin.
    """
    feedback = Feedback(
        user_id=current_user.id,
        type=data.type,
        title=data.title,
        content=data.content,
    )
    await feedback.insert()

    # Build response
    resp = FeedbackResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        userName=f"{current_user.first_name} {current_user.last_name}",
        userEmail=current_user.email,
        type=feedback.type,
        title=feedback.title,
        content=feedback.content,
        status=feedback.status,
        admin_notes=feedback.admin_notes,
        created_at=feedback.created_at,
    )

    return BaseResponse(
        status="success",
        message="Feedback submitted successfully",
        data=resp,
    )


@router.get("/admin", response_model=BaseResponse[List[FeedbackResponse]])
async def list_feedback_admin(
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] List all user feedback items.
    """
    # Fetch all feedback sorted by creation date (newest first)
    feedbacks = await Feedback.find_all().sort(-Feedback.created_at).to_list()

    # Fetch all users to map details
    users = await User.find_all().to_list()
    user_map = {u.id: u for u in users}

    response_data = []
    for f in feedbacks:
        owner = user_map.get(f.user_id)
        name = f"{owner.first_name} {owner.last_name}" if owner else "Unknown User"
        email = owner.email if owner else "Unknown Email"

        response_data.append(
            FeedbackResponse(
                id=f.id,
                user_id=f.user_id,
                userName=name,
                userEmail=email,
                type=f.type,
                title=f.title,
                content=f.content,
                status=f.status,
                admin_notes=f.admin_notes,
                created_at=f.created_at,
            )
        )

    return BaseResponse(
        status="success",
        message="Feedback list retrieved successfully",
        data=response_data,
    )


@router.patch("/admin/{id}/status", response_model=BaseResponse[FeedbackResponse])
async def update_feedback_status_admin(
    id: str,
    data: FeedbackUpdateStatusSchema,
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Update status and admin notes of a feedback item.
    """
    from beanie import PydanticObjectId

    try:
        feedback = await Feedback.get(PydanticObjectId(id))
    except Exception:
        raise CustomException("Feedback item not found", status_code=404)

    if not feedback:
        raise CustomException("Feedback item not found", status_code=404)

    feedback.status = data.status
    if data.admin_notes is not None:
        feedback.admin_notes = data.admin_notes

    await feedback.save()

    # Get owner info
    owner = await User.get(feedback.user_id)
    name = f"{owner.first_name} {owner.last_name}" if owner else "Unknown User"
    email = owner.email if owner else "Unknown Email"

    resp = FeedbackResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        userName=name,
        userEmail=email,
        type=feedback.type,
        title=feedback.title,
        content=feedback.content,
        status=feedback.status,
        admin_notes=feedback.admin_notes,
        created_at=feedback.created_at,
    )

    return BaseResponse(
        status="success",
        message="Feedback status updated successfully",
        data=resp,
    )


@router.delete("/admin/{id}", response_model=BaseResponse[None])
async def delete_feedback_admin(
    id: str,
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Delete a feedback item.
    """
    from beanie import PydanticObjectId

    try:
        feedback = await Feedback.get(PydanticObjectId(id))
    except Exception:
        raise CustomException("Feedback item not found", status_code=404)

    if not feedback:
        raise CustomException("Feedback item not found", status_code=404)

    await feedback.delete()

    return BaseResponse(
        status="success",
        message="Feedback item deleted successfully",
        data=None,
    )
