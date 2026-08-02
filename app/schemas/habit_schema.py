from typing import List, Optional
from pydantic import BaseModel, Field


class PinSetSchema(BaseModel):
    pin: str = Field(..., pattern=r"^\d{4}$")


class PinVerifySchema(BaseModel):
    pin: str = Field(..., pattern=r"^\d{4}$")


class PinResetSchema(BaseModel):
    account_password: str
    new_pin: str = Field(..., pattern=r"^\d{4}$")


class BadHabitCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    target_days: int = Field(default=90, ge=1, le=1000)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class RelapseSchema(BaseModel):
    relapse_reason: Optional[str] = Field(None, max_length=500)


class JournalLogSchema(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    struggle_level: str = Field(..., pattern=r"^(easy|moderate|tough)$")
    notes: Optional[str] = Field(None, max_length=1000)
    triggers: List[str] = Field(default_factory=list)


class AdminHabitLimitSchema(BaseModel):
    max_bad_habits_limit: int = Field(..., ge=1, le=50)
