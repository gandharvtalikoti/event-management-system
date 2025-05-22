from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.schemas.event import EventCreate, EventRead, EventUpdate
from app.models.event import Event
from app.models.user import User
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.permission import EventPermission
from app.models.version import EventVersion
from app.schemas.version import EventVersionRead
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


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    event = session.get(Event, event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Permission check
    if event.owner_id != user.id:
        permission = session.exec(
            select(EventPermission).where(
                EventPermission.event_id == event_id,
                EventPermission.user_id == user.id
            )
        ).first()
        if not permission or permission.role not in ["owner", "editor"]:
            raise HTTPException(status_code=403, detail="No permission to edit")

    # Save previous version
    latest_version = session.exec(
        select(EventVersion)
        .where(EventVersion.event_id == event_id)
        .order_by(EventVersion.version_number.desc())
    ).first()

    version_number = (latest_version.version_number + 1) if latest_version else 1

    version = EventVersion(
        event_id=event.id,
        version_number=version_number,
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        location=event.location,
        updated_by=user.id
    )
    session.add(version)

    # Apply updates
    event.title = event_update.title or event.title
    event.description = event_update.description or event.description
    event.start_time = event_update.start_time or event.start_time
    event.end_time = event_update.end_time or event.end_time
    event.location = event_update.location or event.location

    session.commit()
    session.refresh(event)
    return event

@router.get("/{event_id}/history/{version_id}", response_model=EventVersionRead)
def get_version(
    event_id: int,
    version_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    version = session.get(EventVersion, version_id)
    if not version or version.event_id != event_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post("/{event_id}/rollback/{version_id}", response_model=EventRead)
def rollback_event(
    event_id: int,
    version_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    event = session.get(Event, event_id)
    version = session.get(EventVersion, version_id)

    if not event or not version or version.event_id != event_id:
        raise HTTPException(status_code=404, detail="Event or version not found")

    if event.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only owner can rollback")

    # Save rollback as a new version
    latest_version = session.exec(
        select(EventVersion)
        .where(EventVersion.event_id == event_id)
        .order_by(EventVersion.version_number.desc())
    ).first()

    rollback_version_number = (latest_version.version_number + 1) if latest_version else 1

    rollback_version = EventVersion(
        event_id=event_id,
        version_number=rollback_version_number,
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        location=event.location,
        updated_by=user.id
    )
    session.add(rollback_version)

    # Rollback event
    event.title = version.title
    event.description = version.description
    event.start_time = version.start_time
    event.end_time = version.end_time
    event.location = version.location

    session.commit()
    session.refresh(event)
    return event
