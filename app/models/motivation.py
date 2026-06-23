from datetime import datetime
from beanie import Document
from pydantic import Field


class Motivation(Document):
    title: str
    content: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Settings:
        collection_name = "motivations"

    def __repr__(self) -> str:
        return f"<Motivation(id={self.id}, title={self.title})>"
