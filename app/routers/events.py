from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.schemas.event import EventCreate, EventRead
from app.models.event import Event
from app.models.user import User
from app.core.database import get_session
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/", response_model=EventRead)
def create_event(
    event: EventCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    new_event = Event(**event.dict(), owner_id=user.id)
    session.add(new_event)
    session.commit()
    session.refresh(new_event)
    return new_event


@router.get("/", response_model=list[EventRead])
def list_events(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # Fetch events where user is owner or has permissions
    events = session.exec(
        select(Event).where(Event.owner_id == user.id)
    ).all()
    return events
