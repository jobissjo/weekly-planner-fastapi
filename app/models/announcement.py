from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class Announcement(Document):
    title: str
    description: str
    banner_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Settings:
        collection_name = "announcements"

    def __repr__(self) -> str:
        return f"<Announcement(id={self.id}, title={self.title})>"
