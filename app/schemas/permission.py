
from pydantic import BaseModel
from app.models.user import RoleEnum

class ShareUserPermission(BaseModel):
    user_id: int
    role: RoleEnum

class PermissionRead(BaseModel):
    id: int
    user_id: int
    event_id: int
    role: RoleEnum

    class Config:
        orm_mode = True
