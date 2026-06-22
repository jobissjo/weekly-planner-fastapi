from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, File, Form
from app.core.permissions import any_user_role
from app.models import User
from app.schemas.common_schema import BaseResponse
from app.schemas.user_schema import ProfileUpdateSchema, ProfileUpdateForm

from app.services import EmailService, UserService


router = APIRouter(prefix="/user", tags=["User"])

email_service = EmailService()
user_service = UserService(email_service=email_service)

@router.get("/",)
async def get_user(user:User=Depends(any_user_role)):
    return user

@router.patch("/", response_model=BaseResponse[None])
async def update_profile(
    data: ProfileUpdateSchema,
    current_user: User = Depends(any_user_role),
):
    await user_service.update_profile(str(current_user.id), data)
    return BaseResponse(status="success", message="Profile updated successfully", data=None)

@router.patch("form-upload/", response_model=BaseResponse[None])
async def update_profile_form(
    form_data: ProfileUpdateForm = Depends(),
    current_user: User = Depends(any_user_role),
):
    await user_service.update_profile_form(str(current_user.id), form_data)
    return BaseResponse(status="success", message="Profile updated successfully", data=None)