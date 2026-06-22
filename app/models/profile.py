from typing import Optional, TYPE_CHECKING
from beanie import Document, Link
from pydantic import Field


if TYPE_CHECKING:
    from app.models.user import User


class Profile(Document):
    user: Optional[Link["User"]] = Field(default=None, unique=True, link_type="User.profile")
    bio: Optional[str] = Field(default=None, max_length=500)
    profile_picture_url: Optional[str] = Field(default=None, max_length=255)

    class Settings:
        collection_name = "profiles"

    def __repr__(self):
        return f"<Profile(id={self.id}, user={self.user})>"


