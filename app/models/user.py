from datetime import datetime
from typing import Optional

from beanie import Document, Link
from pydantic import Field

from app.models.enums import EmailType, UserRole
from app.models.profile import Profile


class User(Document):
    email: str = Field(unique=True, index=True)
    password: Optional[str] = None
    google_id: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    first_name: str
    last_name: str
    role: UserRole = UserRole.USER
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    profile: Optional[Link[Profile]] = Field(default=None, link_type="Profile.user")
    email_settings: Optional[Link["EmailSetting"]] = Field(
        default=None, link_type="EmailSetting.user"
    )

    class Settings:
        collection_name = "users"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class TempUserOTP(Document):
    email: str = Field(unique=True, index=True)
    otp: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Settings:
        collection_name = "temp_user_otp"

    def __repr__(self) -> str:
        return f"<TempUserOTP(id={self.id}, email={self.email})>"


class EmailSetting(Document):
    email: str = Field(unique=True, index=True)
    email_type: EmailType = EmailType.SMTP
    user: Optional[Link[User]] = Field(default=None, link_type="User.email_settings")
    password: str
    host: str
    port: int
    is_active: bool = True
    is_admin_mail: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Settings:
        collection_name = "email_settings"

    def __repr__(self) -> str:
        return f"<EmailSetting(id={self.id}, email={self.email})>"
