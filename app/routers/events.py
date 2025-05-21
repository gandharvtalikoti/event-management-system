from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.schemas.event import EventCreate, EventRead
from app.models.event import Event
from app.models.user import User
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.permission import EventPermission
from app.schemas.permission import ShareUserPermission, PermissionRead

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



@router.post("/{event_id}/share", response_model=list[PermissionRead])
def share_event(
    event_id: int,
    permissions: list[ShareUserPermission],
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    event = session.get(Event, event_id)
    if not event or event.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only owner can share event")

    created = []
    for p in permissions:
        existing = session.exec(
            select(EventPermission).where(
                EventPermission.event_id == event_id,
                EventPermission.user_id == p.user_id
            )
        ).first()
        if existing:
            existing.role = p.role  # update existing
        else:
            permission = EventPermission(event_id=event_id, user_id=p.user_id, role=p.role)
            session.add(permission)
            created.append(permission)

    session.commit()
    return created

@router.get("/{event_id}/permissions", response_model=list[PermissionRead])
def get_event_permissions(
    event_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    event = session.get(Event, event_id)
    if not event or event.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only owner can view permissions")

    return session.exec(
        select(EventPermission).where(EventPermission.event_id == event_id)
    ).all()

@router.put("/{event_id}/permissions/{user_id}", response_model=PermissionRead)
def update_permission(
    event_id: int,
    user_id: int,
    update: ShareUserPermission,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    event = session.get(Event, event_id)
    if not event or event.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only owner can update permissions")

    permission = session.exec(
        select(EventPermission).where(
            EventPermission.event_id == event_id,
            EventPermission.user_id == user_id
        )
    ).first()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    permission.role = update.role
    session.commit()
    session.refresh(permission)
    return permission

@router.delete("/{event_id}/permissions/{user_id}")
def delete_permission(
    event_id: int,
    user_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    event = session.get(Event, event_id)
    if not event or event.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only owner can remove permissions")

    permission = session.exec(
        select(EventPermission).where(
            EventPermission.event_id == event_id,
            EventPermission.user_id == user_id
        )
    ).first()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    session.delete(permission)
    session.commit()
    return {"detail": "Permission removed"}