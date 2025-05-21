from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from app.models.user import User
from app.models.event import Event
from app.models.user import RoleEnum

class EventPermission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id")
    user_id: int = Field(foreign_key="user.id")
    role: RoleEnum

