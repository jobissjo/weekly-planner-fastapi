from typing import List

from fastapi import APIRouter, Depends

from app.core.permissions import any_user_role, only_admin
from app.models import User
from app.models.streak import UserStreak
from app.schemas.common_schema import BaseResponse
from app.schemas.user_schema import (
    AuthSettingsSchema,
    ChangePasswordSchema,
    NotificationPreferenceSchema,
    ProfileGamificationUpdateSchema,
    ProfileResponseSchema,
    ProfileUpdateForm,
    ProfileUpdateSchema,
    PushTokenSchema,
)
from app.services import EmailService, UserService

router = APIRouter(prefix="/user", tags=["User"])

email_service = EmailService()
user_service = UserService(email_service=email_service)


@router.get(
    "/",
)
async def get_user(user: User = Depends(any_user_role)):
    return user


@router.get("/profile", response_model=BaseResponse[ProfileResponseSchema])
async def get_profile(
    current_user: User = Depends(any_user_role),
):
    profile = await user_service.get_user_profile(str(current_user.id))
    profile_dict = profile.model_dump()
    if profile.referral_code is None:
        profile_dict["referral_code"] = f"ZEN-{current_user.first_name.upper().replace(' ', '')}2026"
    return BaseResponse(
        status="success",
        message="Profile retrieved successfully",
        data=ProfileResponseSchema(**profile_dict),
    )


@router.patch("/gamification", response_model=BaseResponse[ProfileResponseSchema])
async def update_gamification(
    data: ProfileGamificationUpdateSchema,
    current_user: User = Depends(any_user_role),
):
    profile = await user_service.update_gamification(str(current_user.id), data)
    profile_dict = profile.model_dump()
    if profile.referral_code is None:
        profile_dict["referral_code"] = f"ZEN-{current_user.first_name.upper().replace(' ', '')}2026"
    return BaseResponse(
        status="success",
        message="Gamification profile updated successfully",
        data=ProfileResponseSchema(**profile_dict),
    )


@router.patch("/", response_model=BaseResponse[None])
async def update_profile(
    data: ProfileUpdateSchema,
    current_user: User = Depends(any_user_role),
):
    await user_service.update_profile(str(current_user.id), data)
    return BaseResponse(
        status="success", message="Profile updated successfully", data=None
    )


@router.patch("form-upload/", response_model=BaseResponse[None])
async def update_profile_form(
    form_data: ProfileUpdateForm = Depends(),
    current_user: User = Depends(any_user_role),
):
    await user_service.update_profile_form(str(current_user.id), form_data)
    return BaseResponse(
        status="success", message="Profile updated successfully", data=None
    )


@router.post("/change-password", response_model=BaseResponse[None])
async def change_password(
    data: ChangePasswordSchema,
    current_user: User = Depends(any_user_role),
):
    await user_service.change_password(
        str(current_user.id), data.old_password, data.new_password
    )
    return BaseResponse(
        status="success", message="Password changed successfully", data=None
    )


@router.patch("/notification-preference", response_model=BaseResponse[None])
async def update_notification_preference(
    data: NotificationPreferenceSchema,
    current_user: User = Depends(any_user_role),
):
    await user_service.update_notification_preferences(
        str(current_user.id), data.email_notifications, data.reminders
    )
    return BaseResponse(
        status="success",
        message="Notification preferences updated successfully",
        data=None,
    )


@router.patch("/auth-settings", response_model=BaseResponse[None])
async def update_auth_settings(
    data: AuthSettingsSchema,
    current_user: User = Depends(any_user_role),
):
    await user_service.update_auth_settings(
        str(current_user.id), data.allow_password_login
    )
    return BaseResponse(
        status="success",
        message="Authentication settings updated successfully",
        data=None,
    )


@router.post("/push-token", response_model=BaseResponse[None])
async def register_push_token(
    data: PushTokenSchema,
    current_user: User = Depends(any_user_role),
):
    await user_service.register_push_token(str(current_user.id), data.push_token)
    return BaseResponse(
        status="success", message="Push token registered successfully", data=None
    )


@router.post("/push-token/unregister", response_model=BaseResponse[None])
async def unregister_push_token(
    data: PushTokenSchema,
    current_user: User = Depends(any_user_role),
):
    await user_service.unregister_push_token(str(current_user.id), data.push_token)
    return BaseResponse(
        status="success", message="Push token unregistered successfully", data=None
    )


@router.get("/admin/users", response_model=BaseResponse[List[dict]])
async def admin_list_users(
    admin_user: User = Depends(only_admin),
):
    users = await User.find(User.is_deleted == False).to_list()
    result = []
    for u in users:
        # Get streak for this user
        streak = await UserStreak.find_one(UserStreak.user_id == u.id)
        result.append(
            {
                "id": str(u.id),
                "name": f"{u.first_name} {u.last_name}",
                "email": u.email,
                "role": u.role.value,
                "streakCount": streak.current_streak if streak else 0,
                "streakFreezes": streak.available_freezes if streak else 0,
            }
        )
    return BaseResponse(
        status="success",
        message="Users retrieved successfully",
        data=result,
    )
