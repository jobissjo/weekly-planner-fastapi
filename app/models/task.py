from datetime import datetime
from typing import Optional
from beanie import Document, PydanticObjectId
from pydantic import Field
from app.models.enums import TaskPriority, TaskStatus


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
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection_name = "tasks"

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, user_id={self.user_id})>"
