from datetime import datetime
from typing import Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class MotivationCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    is_active: bool = True


class MotivationUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class MotivationResponse(BaseModel):
    id: PydanticObjectId
    title: str
    content: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
