from fastapi import FastAPI
from app.routers import auth
from app.routers import events
from app.models.user import User
from app.core.database import engine
from sqlmodel import SQLModel

app = FastAPI()

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

app.include_router(auth.router)
app.include_router(events.router)

