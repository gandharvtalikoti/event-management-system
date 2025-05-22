from pydantic import BaseModel
from datetime import datetime

class EventVersionRead(BaseModel):
    id: int
    event_id: int
    version_number: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: str
    updated_by: int
    updated_at: datetime

    class Config:
        orm_mode = True
