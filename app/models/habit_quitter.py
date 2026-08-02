from datetime import datetime
from typing import List, Optional
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class HabitAttempt(BaseModel):
    attempt_number: int
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    days_achieved: int
    relapse_reason: Optional[str] = None


class BadHabit(Document):
    user_id: PydanticObjectId = Field(..., index=True)
    title: str = Field(..., max_length=150)
    description: Optional[str] = Field(default=None, max_length=500)
    target_days: int = 90
    start_date: str  # YYYY-MM-DD
    is_active: bool = True
    current_attempt_number: int = 1
    attempts: List[HabitAttempt] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "bad_habits"


class HabitJournalLog(Document):
    habit_id: PydanticObjectId = Field(..., index=True)
    user_id: PydanticObjectId = Field(..., index=True)
    date: str  # YYYY-MM-DD
    struggle_level: str = "easy"  # "easy" | "moderate" | "tough"
    notes: Optional[str] = Field(default=None, max_length=1000)
    triggers: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "habit_journal_logs"


class HabitVaultPin(Document):
    user_id: PydanticObjectId = Field(..., unique=True, index=True)
    pin_hash: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "habit_vault_pins"


class SystemConfig(Document):
    key: str = Field(..., unique=True, index=True)
    value: str

    class Settings:
        collection_name = "system_configs"
