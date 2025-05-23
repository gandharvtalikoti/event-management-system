from typing import List
from app.models.notification import Notification
from app.routers.notifications import notify_user
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.schemas.event import EventCreate, EventRead, EventUpdate, EventBatchCreate
from app.models.event import Event
from app.models.user import User
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.permission import EventPermission
from app.models.version import EventVersion
from app.schemas.version import EventVersionRead
from app.schemas.permission import ShareUserPermission, PermissionRead
from app.services.diff import diff_versions
from sqlalchemy import and_
from datetime import datetime



router = APIRouter(prefix="/api/events", tags=["events"])


def check_conflict(session: Session, owner_id: int, start_time: datetime, end_time: datetime, exclude_event_id: int | None = None):
    """
    Raise 409 if the owner already has an event overlapping [start_time, end_time].
    """
    query = select(Event).where(
        Event.owner_id == owner_id,
        Event.start_time < end_time,
        Event.end_time > start_time,
    )
    if exclude_event_id is not None:
        query = query.where(Event.id != exclude_event_id)

    conflict = session.exec(query).first()
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Time conflict with event: {conflict.title}, event ID {conflict.id},"
        )



@router.post("/", response_model=EventRead)
def create_event(
    event_create: EventCreate,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    # Conflict check
    check_conflict(session, owner_id=user.id,
                   start_time=event_create.start_time,
                   end_time=event_create.end_time)

    new_event = Event(**event_create.dict(), owner_id=user.id)
    session.add(new_event)
    session.commit()
    session.refresh(new_event)

    # Notification: owner gets a “created” notice
    notif = Notification(
        user_id=user.id,
        event_id=new_event.id,
        message=f"Event '{new_event.title}' created."
    )
    session.add(notif)
    session.commit()

    # Push real-time update (if WS client connected)
    datetime_now = datetime.utcnow().isoformat()
    # (fire-and-forget)
    _ = notify_user(user.id, {
        "type": "event_created",
        "event_id": new_event.id,
        "timestamp": datetime_now
    })

    return new_event


@router.post("/{event_id}/share", response_model=list[PermissionRead])
def share_event(
    event_id: int,
    permissions: list[ShareUserPermission],
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
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
            existing.role = p.role
        else:
            perm = EventPermission(
                event_id=event_id,
                user_id=p.user_id,
                role=p.role
            )
            session.add(perm)
            created.append(perm)

        # Notification per shared user
        notif = Notification(
            user_id=p.user_id,
            event_id=event_id,
            message=f"You were granted '{p.role}' access to event '{event.title}'."
        )
        session.add(notif)

    session.commit()

    # Push real-time notifications for each shared user
    datetime_now = datetime.utcnow().isoformat()
    for p in permissions:
        _ = notify_user(p.user_id, {
            "type": "event_shared",
            "event_id": event_id,
            "role": p.role.value,
            "timestamp": datetime_now
        })

    return created


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Permission check
    if event.owner_id != user.id:
        perm = session.exec(
            select(EventPermission).where(
                EventPermission.event_id == event_id,
                EventPermission.user_id == user.id
            )
        ).first()
        if not perm or perm.role not in ("owner", "editor"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to edit")

    # Snapshot version
    latest = session.exec(
        select(EventVersion)
        .where(EventVersion.event_id == event_id)
        .order_by(EventVersion.version_number.desc())
    ).first()
    next_version = (latest.version_number + 1) if latest else 1

    session.add(EventVersion(
        event_id=event.id,
        version_number=next_version,
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        location=event.location,
        updated_by=user.id
    ))

    # Conflict check
    new_start = event_update.start_time or event.start_time
    new_end   = event_update.end_time   or event.end_time
    check_conflict(session,
                   owner_id=event.owner_id,
                   start_time=new_start,
                   end_time=new_end,
                   exclude_event_id=event_id)

    # Apply updates
    event.title       = event_update.title       or event.title
    event.description = event_update.description or event.description
    event.start_time  = new_start
    event.end_time    = new_end
    event.location    = event_update.location    or event.location

    session.commit()
    session.refresh(event)

    # Notification to owner and all shared users
    # Gather recipients: owner + any EventPermission.user_id
    recipients = {event.owner_id} | {
        perm.user_id
        for perm in session.exec(
            select(EventPermission).where(EventPermission.event_id == event_id)
        ).all()
    }

    notif_objs = []
    datetime_now = datetime.utcnow().isoformat()
    for uid in recipients:
        notif = Notification(
            user_id=uid,
            event_id=event.id,
            message=f"Event '{event.title}' was updated."
        )
        session.add(notif)
        notif_objs.append(notif)
        # real-time push
        _ = notify_user(uid, {
            "type": "event_updated",
            "event_id": event.id,
            "timestamp": datetime_now
        })

    session.commit()

    return event


# @router.post("/", response_model=EventRead)
# def create_event(
#     event_create: EventCreate,
#     session: Session = Depends(get_session),
#     user=Depends(get_current_user),
# ):
#     # Conflict check for this new event
#     check_conflict(
#         session,
#         owner_id=user.id,
#         start_time=event_create.start_time,
#         end_time=event_create.end_time
#     )

#     new_event = Event(**event_create.dict(), owner_id=user.id)
#     session.add(new_event)
#     session.commit()
#     session.refresh(new_event)
#     return new_event

# @router.put("/{event_id}", response_model=EventRead)
# def update_event(
#     event_id: int,
#     event_update: EventUpdate,
#     session: Session = Depends(get_session),
#     user=Depends(get_current_user),
# ):
#     event = session.get(Event, event_id)
#     if not event:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

#     # Permission check (owner or editor)
#     if event.owner_id != user.id:
#         perm = session.exec(
#             select(EventPermission).where(
#                 EventPermission.event_id == event_id,
#                 EventPermission.user_id == user.id
#             )
#         ).first()
#         if not perm or perm.role not in ("owner", "editor"):
#             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to edit")

#     # Save previous version snapshot
#     latest = session.exec(
#         select(EventVersion)
#         .where(EventVersion.event_id == event_id)
#         .order_by(EventVersion.version_number.desc())
#     ).first()
#     next_version = (latest.version_number + 1) if latest else 1

#     session.add(EventVersion(
#         event_id=event.id,
#         version_number=next_version,
#         title=event.title,
#         description=event.description,
#         start_time=event.start_time,
#         end_time=event.end_time,
#         location=event.location,
#         updated_by=user.id
#     ))

#     # Determine new times for conflict check
#     new_start = event_update.start_time or event.start_time
#     new_end   = event_update.end_time   or event.end_time

#     # Conflict check against *owner*’s other events
#     check_conflict(
#         session,
#         owner_id=event.owner_id,
#         start_time=new_start,
#         end_time=new_end,
#         exclude_event_id=event_id
#     )

#     # Apply updates
#     event.title       = event_update.title       or event.title
#     event.description = event_update.description or event.description
#     event.start_time  = new_start
#     event.end_time    = new_end
#     event.location    = event_update.location    or event.location

#     session.commit()
#     session.refresh(event)
#     return event

# @router.post("/{event_id}/share", response_model=list[PermissionRead])
# def share_event(
#     event_id: int,
#     permissions: list[ShareUserPermission],
#     session: Session = Depends(get_session),
#     user: User = Depends(get_current_user)
# ):
#     event = session.get(Event, event_id)
#     if not event or event.owner_id != user.id:
#         raise HTTPException(status_code=403, detail="Only owner can share event")

#     created = []
#     for p in permissions:
#         existing = session.exec(
#             select(EventPermission).where(
#                 EventPermission.event_id == event_id,
#                 EventPermission.user_id == p.user_id
#             )
#         ).first()
#         if existing:
#             existing.role = p.role  # update existing
#         else:
#             permission = EventPermission(event_id=event_id, user_id=p.user_id, role=p.role)
#             session.add(permission)
#             created.append(permission)

#     session.commit()
#     return created


# @router.get("/", response_model=list[EventRead])
# def list_events(
#     session: Session = Depends(get_session),
#     user: User = Depends(get_current_user),
# ):
#     # Fetch events where user is owner or has permissions
#     events = session.exec(
#         select(Event).where(Event.owner_id == user.id)
#     ).all()
#     return events


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



@router.get("/{event_id}/changelog", response_model=list[EventVersionRead], tags=["changelog"])
def get_changelog(
    event_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # Ensure user can view (owner/editor/viewer)
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    # Optionally check sharing permissions here...
    
    versions = session.exec(
        select(EventVersion)
        .where(EventVersion.event_id == event_id)
        .order_by(EventVersion.version_number)
    ).all()
    return versions



@router.get("/{event_id}/diff/{v1_id}/{v2_id}", tags=["changelog"])
def get_diff(
    event_id: int,
    v1_id: int,
    v2_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    v1 = session.get(EventVersion, v1_id)
    v2 = session.get(EventVersion, v2_id)
    if not v1 or not v2 or v1.event_id != event_id or v2.event_id != event_id:
        raise HTTPException(404, "One or both versions not found")
    return diff_versions(v1, v2)


@router.post("/batch", response_model=List[EventRead], tags=["batch"])
def create_events_batch(
    batch: EventBatchCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    created = []
    try:
        for e in batch.events:
            # conflict check per event
            check_conflict(session, user.id, e.start_time, e.end_time)
            ev = Event(**e.dict(), owner_id=user.id)
            session.add(ev)
            created.append(ev)
        session.commit()
        for ev in created:
            session.refresh(ev)
        return created
    except HTTPException:
        session.rollback()
        raise   # re-raise conflict or permission errors
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(500, detail="Batch creation failed")
