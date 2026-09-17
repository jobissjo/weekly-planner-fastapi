from datetime import datetime
from typing import Any, Dict, List, Optional
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core.permissions import any_user_role, only_admin
from app.models import User
from app.models.enums import FeedbackStatus
from app.models.feedback import Feedback
from app.schemas.common_schema import BaseResponse
from app.schemas.feedback_schema import (
    FeedbackCreateSchema,
    FeedbackProviderUpdateSchema,
    FeedbackResponse,
    FeedbackStatsResponse,
    FeedbackUpdateStatusSchema,
)
from app.services.feedback_agent_service import FeedbackAgentService
from app.utils.common import CustomException

router = APIRouter(prefix="/feedback", tags=["Feedback"])
feedback_agent_service = FeedbackAgentService()


def _build_feedback_response(f: Feedback, owner: Optional[User]) -> FeedbackResponse:
    name = f"{owner.first_name} {owner.last_name}" if owner else "Unknown User"
    email = owner.email if owner else "Unknown Email"

    return FeedbackResponse(
        id=f.id,
        user_id=f.user_id,
        userName=name,
        userEmail=email,
        type=f.type,
        title=f.title,
        content=f.content,
        status=f.status,
        admin_notes=f.admin_notes,
        is_critical=f.is_critical,
        severity=f.severity,
        sentiment=f.sentiment,
        ai_analysis=f.ai_analysis,
        ai_reply=f.ai_reply,
        ai_suggested_solution=f.ai_suggested_solution,
        admin_solution=f.admin_solution,
        resolved_at=f.resolved_at,
        created_at=f.created_at,
        updated_at=f.updated_at,
    )


@router.post("", response_model=BaseResponse[FeedbackResponse])
async def create_feedback(
    data: FeedbackCreateSchema,
    current_user: User = Depends(any_user_role),
):
    """
    Submit feedback, a report, or a suggestion.
    Automatically analyzed by the AI Feedback Agent (Gemini/Groq) to determine
    sentiment, severity, automated user reply, and admin triage solutions.
    """
    user_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email

    # Run AI Agent
    ai_result = await feedback_agent_service.process_feedback(
        feedback_type=data.type.value,
        title=data.title,
        content=data.content,
        user_name=user_name,
    )

    feedback = Feedback(
        user_id=current_user.id,
        type=data.type,
        title=data.title,
        content=data.content,
        status=FeedbackStatus.PENDING,
        is_critical=ai_result.get("is_critical", False),
        severity=ai_result.get("severity", "medium"),
        sentiment=ai_result.get("sentiment", "neutral"),
        ai_analysis=ai_result.get("ai_analysis"),
        ai_reply=ai_result.get("ai_reply"),
        ai_suggested_solution=ai_result.get("ai_suggested_solution"),
    )
    await feedback.insert()

    resp = _build_feedback_response(feedback, current_user)
    return BaseResponse(
        status="success",
        message="Feedback processed and submitted successfully",
        data=resp,
    )


@router.get("/my", response_model=BaseResponse[List[FeedbackResponse]])
async def get_my_feedback(
    current_user: User = Depends(any_user_role),
):
    """
    Retrieve all feedback items submitted by the current user,
    including AI responses and Admin solutions.
    """
    feedbacks = await Feedback.find(Feedback.user_id == current_user.id).sort(-Feedback.created_at).to_list()
    data = [_build_feedback_response(f, current_user) for f in feedbacks]

    return BaseResponse(
        status="success",
        message="User feedback history retrieved successfully",
        data=data,
    )


@router.get("/admin", response_model=BaseResponse[List[FeedbackResponse]])
async def list_feedback_admin(
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] List all user feedback items with AI triage details.
    """
    feedbacks = await Feedback.find_all().sort(-Feedback.created_at).to_list()
    users = await User.find_all().to_list()
    user_map = {u.id: u for u in users}

    response_data = [_build_feedback_response(f, user_map.get(f.user_id)) for f in feedbacks]
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
    [ADMIN ONLY] Update status, admin notes, and provide an official admin solution to the user.
    """
    try:
        feedback = await Feedback.get(PydanticObjectId(id))
    except Exception:
        raise CustomException("Feedback item not found", status_code=404)

    if not feedback:
        raise CustomException("Feedback item not found", status_code=404)

    feedback.status = data.status
    if data.admin_notes is not None:
        feedback.admin_notes = data.admin_notes
    if data.admin_solution is not None:
        feedback.admin_solution = data.admin_solution

    if data.status == FeedbackStatus.RESOLVED and not feedback.resolved_at:
        feedback.resolved_at = datetime.utcnow()
    elif data.status != FeedbackStatus.RESOLVED:
        feedback.resolved_at = None

    feedback.updated_at = datetime.utcnow()
    await feedback.save()

    owner = await User.get(feedback.user_id)
    resp = _build_feedback_response(feedback, owner)

    return BaseResponse(
        status="success",
        message="Feedback updated successfully",
        data=resp,
    )


@router.post("/admin/{id}/reanalyze", response_model=BaseResponse[FeedbackResponse])
async def reanalyze_feedback_admin(
    id: str,
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Re-run the AI Feedback Agent (Gemini or Groq) on this feedback item.
    """
    try:
        feedback = await Feedback.get(PydanticObjectId(id))
    except Exception:
        raise CustomException("Feedback item not found", status_code=404)

    if not feedback:
        raise CustomException("Feedback item not found", status_code=404)

    owner = await User.get(feedback.user_id)
    user_name = f"{owner.first_name} {owner.last_name}".strip() if owner else "User"

    ai_result = await feedback_agent_service.process_feedback(
        feedback_type=feedback.type.value,
        title=feedback.title,
        content=feedback.content,
        user_name=user_name,
    )

    feedback.is_critical = ai_result.get("is_critical", False)
    feedback.severity = ai_result.get("severity", "medium")
    feedback.sentiment = ai_result.get("sentiment", "neutral")
    feedback.ai_analysis = ai_result.get("ai_analysis")
    feedback.ai_reply = ai_result.get("ai_reply")
    feedback.ai_suggested_solution = ai_result.get("ai_suggested_solution")
    feedback.updated_at = datetime.utcnow()
    await feedback.save()

    resp = _build_feedback_response(feedback, owner)
    return BaseResponse(
        status="success",
        message="Feedback re-analyzed with AI Agent successfully",
        data=resp,
    )


@router.get("/admin/provider", response_model=BaseResponse[Dict[str, Any]])
async def get_feedback_ai_provider(
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Get current AI Agent provider selection ('groq' or 'gemini').
    """
    status = await feedback_agent_service.get_provider_status()
    return BaseResponse(
        status="success",
        message="AI provider status retrieved",
        data=status,
    )


@router.patch("/admin/provider", response_model=BaseResponse[Dict[str, Any]])
async def set_feedback_ai_provider(
    body: FeedbackProviderUpdateSchema,
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Toggle or select AI Agent provider ('groq' or 'gemini').
    """
    updated = await feedback_agent_service.set_selected_provider(body.provider)
    status = await feedback_agent_service.get_provider_status()
    return BaseResponse(
        status="success",
        message=f"Feedback AI Agent provider set to {updated.upper()}",
        data=status,
    )


@router.get("/admin/stats", response_model=BaseResponse[FeedbackStatsResponse])
async def get_feedback_stats(
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Aggregated statistics for feedback triage.
    """
    feedbacks = await Feedback.find_all().to_list()
    total = len(feedbacks)
    pending = sum(1 for f in feedbacks if f.status == FeedbackStatus.PENDING)
    in_progress = sum(1 for f in feedbacks if f.status == FeedbackStatus.IN_PROGRESS)
    resolved = sum(1 for f in feedbacks if f.status == FeedbackStatus.RESOLVED)
    critical_unresolved = sum(
        1 for f in feedbacks if f.is_critical and f.status != FeedbackStatus.RESOLVED
    )
    positive_count = sum(1 for f in feedbacks if f.sentiment == "positive")
    critical_count = sum(1 for f in feedbacks if f.is_critical or f.severity == "critical")

    stats = FeedbackStatsResponse(
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        critical_unresolved=critical_unresolved,
        positive_count=positive_count,
        critical_count=critical_count,
    )

    return BaseResponse(
        status="success",
        message="Feedback stats retrieved successfully",
        data=stats,
    )


@router.delete("/admin/{id}", response_model=BaseResponse[None])
async def delete_feedback_admin(
    id: str,
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Delete a feedback item.
    """
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
