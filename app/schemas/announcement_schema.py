from datetime import datetime
from typing import Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class AnnouncementCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=4000)
    banner_url: Optional[str] = None
    is_active: bool = True


class AnnouncementUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=4000)
    banner_url: Optional[str] = None
    is_active: Optional[bool] = None


class AnnouncementResponse(BaseModel):
    id: PydanticObjectId
    title: str
    description: str
    bannerUrl: Optional[str] = Field(None, validation_alias="banner_url")
    isActive: bool = Field(..., validation_alias="is_active")
    createdAt: datetime = Field(..., validation_alias="created_at")

    model_config = {"from_attributes": True}
