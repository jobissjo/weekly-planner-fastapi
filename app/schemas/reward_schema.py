from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class RewardCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class RewardResponse(BaseModel):
    id: PydanticObjectId
    user_id: Optional[PydanticObjectId] = None
    title: str
    description: Optional[str] = None
    is_favorite: bool
    is_generic: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
