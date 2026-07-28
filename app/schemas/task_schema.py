from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field, field_validator

from app.models.enums import RecurrencePattern, TaskPriority, TaskStatus
from app.models.task import Subtask, TaskAttachment


class TaskCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    startTime: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:mm
    endTime: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:mm
    priority: TaskPriority = TaskPriority.MEDIUM
    isOptional: bool = False
    status: TaskStatus = TaskStatus.PENDING
    recurrence: Optional[RecurrencePattern] = RecurrencePattern.NONE
    subtasks: Optional[List[Subtask]] = None
    attachments: Optional[List[TaskAttachment]] = None
    calendarEventId: Optional[str] = None
    isSyncedToCalendar: Optional[bool] = False
    completionNotes: Optional[str] = None
    completedDate: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator("completedDate", "completionNotes", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        if v == "":
            return None
        return v


class TaskUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    startTime: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    endTime: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    priority: Optional[TaskPriority] = None
    isOptional: Optional[bool] = None
    status: Optional[TaskStatus] = None
    recurrence: Optional[RecurrencePattern] = None
    subtasks: Optional[List[Subtask]] = None
    attachments: Optional[List[TaskAttachment]] = None
    calendarEventId: Optional[str] = None
    isSyncedToCalendar: Optional[bool] = None
    completionNotes: Optional[str] = None
    completedDate: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator("completedDate", "completionNotes", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        if v == "":
            return None
        return v


class TaskResponse(BaseModel):
    id: PydanticObjectId
    title: str
    description: Optional[str] = None
    date: str
    startTime: str
    endTime: str
    priority: TaskPriority
    isOptional: bool
    status: TaskStatus
    recurrence: Optional[RecurrencePattern] = RecurrencePattern.NONE
    subtasks: Optional[List[Subtask]] = None
    attachments: Optional[List[TaskAttachment]] = None
    calendarEventId: Optional[str] = None
    isSyncedToCalendar: Optional[bool] = False
    completionNotes: Optional[str] = None
    completedDate: Optional[str] = None
    createdAt: datetime
    userId: PydanticObjectId = Field(..., validation_alias="user_id")

    model_config = {"from_attributes": True}
