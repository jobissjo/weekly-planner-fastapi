from datetime import datetime
from typing import Optional
from beanie import Document, PydanticObjectId
from pydantic import Field


class Reward(Document):
    user_id: Optional[PydanticObjectId] = Field(default=None, index=True)  # None means generic reward suggested by system
    title: str = Field(..., max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    is_favorite: bool = False  # Whether this is the active reward selected for the week
    is_generic: bool = False  # Whether it is a generic default reward
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "rewards"

    def __repr__(self) -> str:
        return f"<Reward(id={self.id}, title={self.title}, user_id={self.user_id}, is_favorite={self.is_favorite})>"
