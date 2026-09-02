from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends

from app.core.permissions import any_user_role, only_admin
from app.models.user import User
from app.schemas.common_schema import BaseResponse
from app.schemas.task_schema import TaskCreateSchema, TaskResponse
from app.services.gmail_service import GmailService
from app.services.task_service import TaskService
from app.utils.common import CustomException

router = APIRouter(prefix="/gmail", tags=["Gmail & AI Assistant"])
gmail_service = GmailService()
task_service = TaskService()


class GmailStatusResponse(BaseModel):
    connected: bool
    email: Optional[str] = None
    feature_enabled: bool = True


class GmailCallbackBody(BaseModel):
    code: str


class ConvertGmailToTaskBody(BaseModel):
    title: str
    description: Optional[str] = None
    date: str
    startTime: str
    endTime: str
    priority: str = "medium"


class FeatureToggleBody(BaseModel):
    feature_enabled: bool


@router.get("/status", response_model=BaseResponse[GmailStatusResponse])
async def get_gmail_status(current_user: User = Depends(any_user_role)):
    enabled = await gmail_service.is_feature_enabled()
    return BaseResponse(
        status="success",
        message="Gmail status retrieved successfully",
        data=GmailStatusResponse(
            connected=getattr(current_user, "gmail_connected", False),
            email=getattr(current_user, "gmail_email", None),
            feature_enabled=enabled,
        ),
    )


@router.get("/admin/toggle", response_model=BaseResponse[FeatureToggleBody])
async def get_admin_gmail_feature_toggle(admin: User = Depends(only_admin)):
    enabled = await gmail_service.is_feature_enabled()
    return BaseResponse(
        status="success",
        message="Gmail feature toggle setting retrieved",
        data=FeatureToggleBody(feature_enabled=enabled),
    )


@router.patch("/admin/toggle", response_model=BaseResponse[FeatureToggleBody])
async def update_admin_gmail_feature_toggle(
    body: FeatureToggleBody, admin: User = Depends(only_admin)
):
    enabled = await gmail_service.set_feature_enabled(body.feature_enabled)
    return BaseResponse(
        status="success",
        message=f"Gmail feature {'enabled' if enabled else 'disabled'} successfully",
        data=FeatureToggleBody(feature_enabled=enabled),
    )


@router.get("/auth-url", response_model=BaseResponse[str])
async def get_gmail_auth_url(current_user: User = Depends(any_user_role)):
    if not await gmail_service.is_feature_enabled():
        raise CustomException("Gmail integration feature is currently disabled by administrator", 403)
    url = gmail_service.get_oauth_url(current_user)
    return BaseResponse(
        status="success",
        message="Google OAuth URL generated",
        data=url,
    )


@router.post("/callback", response_model=BaseResponse[GmailStatusResponse])
async def gmail_oauth_callback(
    body: GmailCallbackBody, current_user: User = Depends(any_user_role)
):
    if not await gmail_service.is_feature_enabled():
        raise CustomException("Gmail integration feature is currently disabled by administrator", 403)
    res = await gmail_service.exchange_code_for_tokens(body.code, current_user)
    return BaseResponse(
        status="success",
        message="Gmail account connected successfully",
        data=GmailStatusResponse(
            connected=True,
            email=res.get("gmail_email"),
            feature_enabled=True,
        ),
    )


@router.post("/disconnect", response_model=BaseResponse[None])
async def disconnect_gmail(current_user: User = Depends(any_user_role)):
    await gmail_service.disconnect_gmail(current_user)
    return BaseResponse(
        status="success",
        message="Gmail account disconnected",
        data=None,
    )


@router.get("/important-today", response_model=BaseResponse[List[dict]])
async def get_important_gmail_today(current_user: User = Depends(any_user_role)):
    if not await gmail_service.is_feature_enabled():
        raise CustomException("Gmail integration feature is currently disabled by administrator", 403)
    items = await gmail_service.analyze_messages_with_groq(current_user)
    return BaseResponse(
        status="success",
        message="Today's important emails analyzed with Groq AI",
        data=items,
    )


@router.get("/all-messages", response_model=BaseResponse[List[dict]])
async def get_all_gmail_messages(
    q: Optional[str] = None,
    max_results: int = 25,
    current_user: User = Depends(any_user_role),
):
    if not await gmail_service.is_feature_enabled():
        raise CustomException("Gmail integration feature is currently disabled by administrator", 403)
    messages = await gmail_service.fetch_all_messages(current_user, max_results=max_results, query=q)
    return BaseResponse(
        status="success",
        message="Gmail inbox messages retrieved successfully",
        data=messages,
    )


@router.get("/message/{message_id}", response_model=BaseResponse[dict])
async def get_gmail_message_by_id(
    message_id: str,
    current_user: User = Depends(any_user_role),
):
    if not await gmail_service.is_feature_enabled():
        raise CustomException("Gmail integration feature is currently disabled by administrator", 403)
    message = await gmail_service.fetch_message_by_id(current_user, message_id)
    if not message:
        raise CustomException("Email message not found", 404)
    return BaseResponse(
        status="success",
        message="Email message details retrieved successfully",
        data=message,
    )


@router.post("/convert-to-task", response_model=BaseResponse[TaskResponse])
async def convert_gmail_to_task(
    body: ConvertGmailToTaskBody, current_user: User = Depends(any_user_role)
):
    if not await gmail_service.is_feature_enabled():
        raise CustomException("Gmail integration feature is currently disabled by administrator", 403)

    from app.models.enums import TaskPriority

    try:
        prio = TaskPriority(body.priority.lower())
    except ValueError:
        prio = TaskPriority.MEDIUM

    task_schema = TaskCreateSchema(
        title=body.title,
        description=body.description,
        date=body.date,
        startTime=body.startTime,
        endTime=body.endTime,
        priority=prio,
    )

    task = await task_service.create_task(current_user.id, task_schema)
    return BaseResponse(
        status="success",
        message="Email converted to task successfully",
        data=TaskResponse.model_validate(task),
    )
