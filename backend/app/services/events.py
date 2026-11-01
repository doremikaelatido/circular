from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.entities import (
    Connection,
    ConnectionStatus,
    Event,
    EventStatus,
    Notification,
    Participant,
    ParticipantStatus,
    User,
)
from app.schemas.api import EventInput


def utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def accepted_connection_ids(db: Session, user_id: int) -> set[int]:
    rows = db.execute(
        select(Connection.user_low_id, Connection.user_high_id).where(
            Connection.status == ConnectionStatus.ACCEPTED,
            or_(Connection.user_low_id == user_id, Connection.user_high_id == user_id),
        )
    ).all()
    return {high if low == user_id else low for low, high in rows}


def can_access_event(db: Session, user_id: int, event: Event) -> bool:
    if event.creator_id == user_id:
        return True
    is_participant = db.scalar(
        select(exists().where(
            Participant.event_id == event.id,
            Participant.user_id == user_id,
            Participant.status == ParticipantStatus.ACTIVE,
        ))
    )
    if is_participant:
        return True
    from app.models.entities import EventInvitation

    is_invited = db.scalar(select(exists().where(
        EventInvitation.event_id == event.id,
        EventInvitation.user_id == user_id,
    )))
    if is_invited:
        return True
    connections = accepted_connection_ids(db, user_id)
    if not connections:
        return False
    if event.creator_id in connections:
        return True
    return bool(db.scalar(
        select(exists().where(
            Participant.event_id == event.id,
            Participant.user_id.in_(connections),
            Participant.status == ParticipantStatus.ACTIVE,
        ))
    ))


def visible_events_query(db: Session, user_id: int, view: str, starts_at: datetime, ends_at: datetime):
    participation = exists().where(
        Participant.event_id == Event.id,
        Participant.user_id == user_id,
        Participant.status == ParticipantStatus.ACTIVE,
    )
    if view == "mine":
        access = or_(Event.creator_id == user_id, participation)
    else:
        connected_ids = accepted_connection_ids(db, user_id)
        access = or_(
            Event.creator_id.in_(connected_ids or {-1}),
            exists().where(
                Participant.event_id == Event.id,
                Participant.user_id.in_(connected_ids or {-1}),
                Participant.status == ParticipantStatus.ACTIVE,
            ),
        )
    return select(Event).where(
        access,
        Event.status == EventStatus.ACTIVE,
        Event.ends_at > datetime.now(UTC),
        Event.starts_at < ends_at,
        Event.ends_at > starts_at,
    ).order_by(Event.starts_at).limit(500)


def create_event(db: Session, creator: User, payload: EventInput) -> Event:
    invited_ids = set(payload.invite_user_ids)
    invited_ids.discard(creator.id)
    if invited_ids and not invited_ids.issubset(accepted_connection_ids(db, creator.id)):
        raise ValueError("Only accepted connections can be invited")
    now = datetime.now(UTC)
    event = Event(
        creator_id=creator.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        starts_at=payload.starts_at.astimezone(UTC),
        ends_at=payload.ends_at.astimezone(UTC),
        location=payload.location,
        status=EventStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    db.add(event)
    db.flush()
    if invited_ids:
        from app.models.entities import EventInvitation
        for user_id in invited_ids:
            db.add(EventInvitation(
                event_id=event.id,
                user_id=user_id,
                invited_by_id=creator.id,
                created_at=now,
            ))
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event: Event, payload: EventInput) -> Event:
    now = datetime.now(UTC)
    event.title = payload.title
    event.description = payload.description
    event.category = payload.category
    event.starts_at = payload.starts_at.astimezone(UTC)
    event.ends_at = payload.ends_at.astimezone(UTC)
    event.location = payload.location
    event.updated_at = now
    db.commit()
    db.refresh(event)
    return event


def leave_event(db: Session, event: Event, user: User) -> None:
    participant = db.scalar(select(Participant).where(
        Participant.event_id == event.id,
        Participant.user_id == user.id,
    ))
    if participant is None or participant.status != ParticipantStatus.ACTIVE:
        return
    now = datetime.now(UTC)
    leave_action_id = str(uuid4())
    participant.status = ParticipantStatus.LEFT
    participant.left_at = now
    connection_ids = accepted_connection_ids(db, user.id)
    if connection_ids:
        recipients = db.scalars(select(Participant.user_id).where(
            Participant.event_id == event.id,
            Participant.user_id.in_(connection_ids),
            Participant.user_id != user.id,
            Participant.status == ParticipantStatus.ACTIVE,
        )).all()
        db.add_all([
            Notification(
                leave_action_id=leave_action_id,
                recipient_id=recipient_id,
                actor_id=user.id,
                event_id=event.id,
                read=False,
                created_at=now,
            )
            for recipient_id in recipients
        ])
    db.commit()


def event_view(db: Session, event: Event, user_id: int) -> dict[str, object]:
    count = db.scalar(
        select(func.count()).select_from(Participant).where(
            Participant.event_id == event.id,
            Participant.status == ParticipantStatus.ACTIVE,
        )
    )
    participating = bool(db.scalar(select(exists().where(
        Participant.event_id == event.id,
        Participant.user_id == user_id,
        Participant.status == ParticipantStatus.ACTIVE,
    ))))
    return {
        "id": event.id,
        "creator_id": event.creator_id,
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "starts_at": event.starts_at,
        "ends_at": event.ends_at,
        "location": event.location,
        "status": event.status,
        "participant_count": int(count or 0),
        "current_user_participating": participating,
        "current_user_is_creator": event.creator_id == user_id,
    }
