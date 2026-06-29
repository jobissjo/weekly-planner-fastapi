from datetime import datetime
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class StreakRule(Document):
    name: str = Field(..., max_length=100)
    required_consecutive_days: int = 3
    freezes_to_grant: int = 1
    max_freezes_allowed: int = 2
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "streak_rules"

    def __repr__(self) -> str:
        return f"<StreakRule(id={self.id}, name={self.name}, active={self.is_active})>"


class UserStreak(Document):
    user_id: PydanticObjectId = Field(..., unique=True, index=True)
    current_streak: int = 0
    longest_streak: int = 0
    available_freezes: int = 0
    last_completed_date: Optional[str] = None  # YYYY-MM-DD
    last_rewarded_streak: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "user_streaks"

    def __repr__(self) -> str:
        return f"<UserStreak(id={self.id}, user_id={self.user_id}, streak={self.current_streak})>"


class StreakRewardHistory(Document):
    user_id: PydanticObjectId = Field(..., index=True)
    rule_id: Optional[PydanticObjectId] = None
    freezes_granted: int = 1
    streak_at_reward: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "streak_reward_history"

    def __repr__(self) -> str:
        return f"<StreakRewardHistory(id={self.id}, user_id={self.user_id}, granted={self.freezes_granted})>"
