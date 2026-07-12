from datetime import datetime
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field

from app.models.enums import FeedbackStatus, FeedbackType


class Feedback(Document):
    user_id: PydanticObjectId = Field(..., index=True)
    type: FeedbackType = FeedbackType.FEEDBACK
    title: str
    content: str
    status: FeedbackStatus = Field(default=FeedbackStatus.PENDING, index=True)
    admin_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Settings:
        collection_name = "feedback"

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, type={self.type}, title={self.title})>"
