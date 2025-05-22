from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime

class EventVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id")
    version_number: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    updated_by: int = Field(foreign_key="user.id")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

