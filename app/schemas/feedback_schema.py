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
    createdAt: datetime = Field(..., validation_alias="created_at")

    model_config = {"from_attributes": True}
