from fastapi import FastAPI
from app.routers import auth
from app.routers import events
# from app.models.user import User
from app.core.database import engine
from sqlmodel import SQLModel

from fastapi import FastAPI

app = FastAPI(
    title="CollabEvents API",
    description="""
    🚀 Collaborative Event Management System API

    This API allows users to create, update, and share events with versioning,
    conflict detection, real-time notifications, and role-based permissions.

    ## Features
    - 🔐 JWT Authentication
    - 🗓️ Event creation, editing & conflict detection
    - 🧑‍🤝‍🧑 Sharing with role-based access
    - 🔄 Versioning with changelogs
    - 🔔 Real-time WebSocket notifications
    """,
    version="1.0.0",
    contact={
        "name": "Gandharv",
        "url": "https://github.com/yourgithub",  # Change if needed
        "email": "youremail@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

app.include_router(auth.router)
app.include_router(events.router)

