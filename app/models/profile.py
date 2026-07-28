from typing import TYPE_CHECKING, Optional

from beanie import Document, Link
from pydantic import Field

if TYPE_CHECKING:
    from app.models.user import User


class Profile(Document):
    user: Optional[Link["User"]] = Field(
        default=None, unique=True, link_type="User.profile"
    )
    bio: Optional[str] = Field(default=None, max_length=500)
    profile_picture_url: Optional[str] = Field(default=None, max_length=255)
    email_notifications: bool = True
    reminders: bool = True
    xp: int = 350
    level: int = 1
    active_theme: str = "system"
    unlocked_themes: list[str] = Field(default_factory=lambda: ["light", "dark", "system"])
    active_border: str = "default"
    unlocked_borders: list[str] = Field(default_factory=lambda: ["default"])

    class Settings:
        collection_name = "profiles"

    def __repr__(self):
        return f"<Profile(id={self.id}, user={self.user})>"
