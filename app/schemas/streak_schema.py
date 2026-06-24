from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class StreakRuleCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    required_consecutive_days: int = Field(default=3, ge=1)
    freezes_to_grant: int = Field(default=1, ge=0)
    max_freezes_allowed: int = Field(default=2, ge=0)
    is_active: bool = Field(default=True)


class StreakRuleUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    required_consecutive_days: Optional[int] = Field(default=None, ge=1)
    freezes_to_grant: Optional[int] = Field(default=None, ge=0)
    max_freezes_allowed: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = Field(default=None)


class StreakRuleResponse(BaseModel):
    id: PydanticObjectId
    name: str
    required_consecutive_days: int
    freezes_to_grant: int
    max_freezes_allowed: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserStreakResponse(BaseModel):
    id: PydanticObjectId
    user_id: PydanticObjectId
    current_streak: int
    longest_streak: int
    available_freezes: int
    last_completed_date: Optional[str] = None
    last_rewarded_streak: int
    updated_at: datetime

    class Config:
        from_attributes = True


class StreakRewardHistoryResponse(BaseModel):
    id: PydanticObjectId
    user_id: PydanticObjectId
    rule_id: Optional[PydanticObjectId] = None
    freezes_granted: int
    streak_at_reward: int
    created_at: datetime

    class Config:
        from_attributes = True


class StreakDayStatus(BaseModel):
    date: str
    status: str

