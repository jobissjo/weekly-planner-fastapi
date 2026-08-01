from datetime import datetime
from typing import List, Optional

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.enums import RecurrencePattern, TaskPriority, TaskStatus


class Subtask(BaseModel):
    id: str
    title: str
    completed: bool = False


class TaskAttachment(BaseModel):
    id: str
    type: str  # "image" | "link"
    url: str
    name: Optional[str] = None


class Task(Document):
    user_id: PydanticObjectId = Field(..., index=True)
    title: str
    description: Optional[str] = None
    date: str  # YYYY-MM-DD format
    startTime: str  # HH:mm format
    endTime: str  # HH:mm format
    priority: TaskPriority = TaskPriority.MEDIUM
    isOptional: bool = False
    status: TaskStatus = TaskStatus.PENDING
    recurrence: Optional[RecurrencePattern] = RecurrencePattern.NONE
    specializedTitle: Optional[str] = None
    subtasks: Optional[List[Subtask]] = None
    attachments: Optional[List[TaskAttachment]] = None
    calendarEventId: Optional[str] = None
    isSyncedToCalendar: Optional[bool] = False
    completionNotes: Optional[str] = None
    completedDate: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "tasks"

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, user_id={self.user_id})>"
