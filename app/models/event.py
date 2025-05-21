from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from app.models.user import User

class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None # e.g. 'daily', 'weekly', 'custom json'
    owner_id: int = Field(foreign_key="user.id")
    owner: Optional["User"] = Relationship(back_populates="events")
