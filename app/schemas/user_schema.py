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
    old_password: str = Field(..., min_length=4)
    new_password: str = Field(..., min_length=4)


class NotificationPreferenceSchema(BaseModel):
    email_notifications: bool
    reminders: bool


class PushTokenSchema(BaseModel):
    push_token: str
