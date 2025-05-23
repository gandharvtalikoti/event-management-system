from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    event_id: Optional[int] = Field(foreign_key="event.id")
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
