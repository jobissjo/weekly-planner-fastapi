from typing import Optional

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, Field

from app.models.enums import UserRole


class LoginEmailSchema(BaseModel):
    email: str
    password: str


class GoogleLoginSchema(BaseModel):
    credential: str


class RegisterSchema(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    otp: str
    role: UserRole = Field(default=UserRole.USER)
    referral_code: Optional[str] = None


class VerifyUserSchema(BaseModel):
    email: str
    otp: str


class EmailVerifySchema(BaseModel):
    first_name: str
    email: str


class EmailVerifyOtpSchema(BaseModel):
    otp: str
    email: str


class ProfileUpdateSchema(BaseModel):
    bio: str | None = Field(default=None, max_length=500)
    profile_picture: str | None = Field(
        default=None, description="Base64-encoded image string"
    )


class ProfileUpdateForm:
    def __init__(
        self,
        profile_picture: Optional[UploadFile] = File(None),
        bio: str = Form(...),
    ):
        self.profile_picture = profile_picture
        self.bio = bio


class ChangePasswordSchema(BaseModel):
    old_password: Optional[str] = Field(None)
    new_password: str = Field(..., min_length=4)


class NotificationPreferenceSchema(BaseModel):
    email_notifications: bool
    reminders: bool


class PushTokenSchema(BaseModel):
    push_token: str


class AuthSettingsSchema(BaseModel):
    allow_password_login: bool


class ProfileGamificationUpdateSchema(BaseModel):
    xp: Optional[int] = None
    level: Optional[int] = None
    active_theme: Optional[str] = None
    unlocked_themes: Optional[list[str]] = None
    active_border: Optional[str] = None
    unlocked_borders: Optional[list[str]] = None


class ProfileResponseSchema(BaseModel):
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    email_notifications: bool = True
    reminders: bool = True
    xp: int = 350
    level: int = 1
    active_theme: str = "system"
    unlocked_themes: list[str] = Field(default_factory=lambda: ["light", "dark", "system"])
    active_border: str = "default"
    unlocked_borders: list[str] = Field(default_factory=lambda: ["default"])
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None
    accountability_partners: list[str] = Field(default_factory=list)


