from fastapi import FastAPI
from app.routers import auth
from app.routers import events
# from app.models.user import User
from app.core.database import engine
from sqlmodel import SQLModel

from fastapi import FastAPI

app = FastAPI(
    title="Collaborative Event Management System",
    description="""
🚀 Collaborative Event Management System API

This API allows users to create, update, and share events with:
- Versioning (full changelogs & rollback)
- Conflict detection (no overlapping events)
- Real-time WebSocket notifications
- Role-based permissions (Owner, Editor, Viewer)

## Quick Links
- 📦 [GitHub Repo](https://github.com/gandharvtalikoti/event-management-system)
- 🌐 [My Portfolio](https://gandharv-portfolio.vercel.app/)

## Features
- 🔐 JWT Authentication  
- 🗓️ Event creation, editing & conflict checks  
- 🧑‍🤝‍🧑 Sharing with granular access control  
- 🔄 Full version history & diff  
- 🔔 Live notifications over WebSocket  
    """,
    version="1.0.0",
    contact={
        "name": "Gandharv Talikoti",
        "url": "https://gandharv-portfolio.vercel.app/",
        "email": "gandharvwork@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "docExpansion": "none",
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
    }
)



@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

app.include_router(auth.router)
app.include_router(events.router)

