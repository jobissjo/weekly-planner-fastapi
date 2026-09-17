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

    # AI Agent fields
    is_critical: bool = Field(default=False, index=True)
    severity: str = Field(default="medium", index=True)  # "critical", "high", "medium", "low"
    sentiment: str = Field(default="neutral", index=True)  # "positive", "neutral", "negative", "critical"
    ai_analysis: Optional[str] = None
    ai_reply: Optional[str] = None
    ai_suggested_solution: Optional[str] = None

    # Admin resolution to user
    admin_solution: Optional[str] = None
    resolved_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "feedback"

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, type={self.type}, title={self.title}, critical={self.is_critical})>"
