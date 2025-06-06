from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class EventCreate(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None

class EventBatchCreate(BaseModel):
    events: List[EventCreate]

class EventRead(BaseModel):
    id: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    is_recurring: bool
    recurrence_pattern: Optional[str]
    owner_id: int

    class Config:
        orm_mode = True

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None

    class Config:
        orm_mode = True
