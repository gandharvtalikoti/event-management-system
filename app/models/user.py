from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
import enum

class RoleEnum(str, enum.Enum):
    owner = "owner"# In the code snippet provided, `editor = "editor"` and `viewer = "viewer"` are
    # defining two members of an enumeration class called `RoleEnum`.
    
    editor = "editor"
    viewer = "viewer"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    hashed_password: str
    role: RoleEnum = RoleEnum.viewer
    is_active: bool = True
    events: List["Event"] = Relationship(back_populates="owner")



