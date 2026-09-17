from datetime import datetime
from typing import Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.models.enums import FeedbackStatus, FeedbackType


class FeedbackCreateSchema(BaseModel):
    type: FeedbackType = FeedbackType.FEEDBACK
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=2000)


class FeedbackUpdateStatusSchema(BaseModel):
    status: FeedbackStatus
    admin_notes: Optional[str] = None
    admin_solution: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: PydanticObjectId
    userId: PydanticObjectId = Field(..., validation_alias="user_id")
    userName: Optional[str] = None
    userEmail: Optional[str] = None
    type: FeedbackType
    title: str
    content: str
    status: FeedbackStatus
    admin_notes: Optional[str] = None

    # AI Agent fields
    is_critical: bool = False
    severity: str = "medium"
    sentiment: str = "neutral"
    ai_analysis: Optional[str] = None
    ai_reply: Optional[str] = None
    ai_suggested_solution: Optional[str] = None

    # Admin Solution
    admin_solution: Optional[str] = None
    resolved_at: Optional[datetime] = None

    createdAt: datetime = Field(..., validation_alias="created_at")
    updatedAt: Optional[datetime] = Field(default=None, validation_alias="updated_at")

    model_config = {"from_attributes": True}


class FeedbackProviderUpdateSchema(BaseModel):
    provider: str  # "groq" or "gemini"


class FeedbackStatsResponse(BaseModel):
    total: int
    pending: int
    in_progress: int
    resolved: int
    critical_unresolved: int
    positive_count: int
    critical_count: int
