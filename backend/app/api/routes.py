from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, Database
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import (
    Connection,
    ConnectionStatus,
    Event,
    EventInvitation,
    EventStatus,
    Notification,
    Participant,
    ParticipantStatus,
    User,
)
from app.schemas.api import (
    AuthResponse,
    ConnectionRequestInput,
    ConnectionView,
    EventInput,
    EventView,
    LoginInput,
    MessageResponse,
    NotificationView,
    RegistrationInput,
    UserSearchView,
    UserView,
)
from app.services.events import (
    accepted_connection_ids,
    can_access_event,
    create_event,
    event_view,
    leave_event,
    update_event,
    utc_datetime,
    visible_events_query,
)

router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["authentication"])
users_router = APIRouter(prefix="/users", tags=["users and connections"])
events_router = APIRouter(prefix="/events", tags=["events"])
calendar_router = APIRouter(prefix="/calendar", tags=["calendar"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@auth_router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegistrationInput, db: Database) -> AuthResponse:
    user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        gender=payload.gender or None,
        created_at=datetime.now(UTC),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists") from None
    db.refresh(user)
    token, expires_in = create_access_token(user.id)
    return AuthResponse(access_token=token, expires_in=expires_in, user=user)


@auth_router.post("/login", response_model=AuthResponse)
def login(payload: LoginInput, db: Database) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect")
    token, expires_in = create_access_token(user.id)
    return AuthResponse(access_token=token, expires_in=expires_in, user=user)


@auth_router.post("/logout", response_model=MessageResponse)
def logout(current_user: CurrentUser) -> MessageResponse:
    return MessageResponse(message="Signed out")


@auth_router.get("/me", response_model=UserView)
def me(current_user: CurrentUser) -> User:
    return current_user


def _pair(user_id: int, other_id: int) -> tuple[int, int]:
    return (min(user_id, other_id), max(user_id, other_id))


@users_router.get("/search", response_model=list[UserSearchView])
def search_users(
    current_user: CurrentUser,
    db: Database,
    q: str = Query(min_length=2, max_length=100),
) -> list[dict[str, object]]:
    query = q.strip()
    if not query:
        return []
    candidates = db.scalars(
        select(User).where(
            User.id != current_user.id,
            or_(User.email == query.casefold(), User.nickname.ilike(f"%{query}%")),
        ).order_by(User.nickname).limit(20)
    ).all()
    return [{"id": user.id, "nickname": user.nickname} for user in candidates]


@users_router.get("/connections", response_model=list[ConnectionView])
def list_connections(current_user: CurrentUser, db: Database) -> list[dict[str, object]]:
    rows = db.execute(
        select(Connection, User).join(
            User,
            User.id == case(
                (Connection.user_low_id == current_user.id, Connection.user_high_id),
                else_=Connection.user_low_id,
            ),
        ).where(
            or_(Connection.user_low_id == current_user.id, Connection.user_high_id == current_user.id),
        ).order_by(Connection.created_at.desc())
    ).all()
    return [
        {
            "id": connection.id,
            "user_id": other.id,
            "nickname": other.nickname,
            "status": connection.status.value,
            "direction": "outgoing" if connection.requester_id == current_user.id else "incoming",
        }
        for connection, other in rows
    ]


@users_router.post("/connections", response_model=ConnectionView, status_code=status.HTTP_201_CREATED)
def request_connection(payload: ConnectionRequestInput, current_user: CurrentUser, db: Database):
    other = db.get(User, payload.user_id)
    if other is None or other.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    low_id, high_id = _pair(current_user.id, other.id)
    connection = db.scalar(select(Connection).where(
        Connection.user_low_id == low_id,
        Connection.user_high_id == high_id,
    ))
    if connection is None:
        connection = Connection(
            user_low_id=low_id,
            user_high_id=high_id,
            requester_id=current_user.id,
            status=ConnectionStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        db.add(connection)
    elif connection.status == ConnectionStatus.ACCEPTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You are already connected")
    elif connection.status == ConnectionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A connection request already exists")
    else:
        connection.requester_id = current_user.id
        connection.status = ConnectionStatus.PENDING
        connection.created_at = datetime.now(UTC)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A connection request already exists") from None
    db.refresh(connection)
    return {
        "id": connection.id,
        "user_id": other.id,
        "nickname": other.nickname,
        "status": connection.status.value,
        "direction": "outgoing",
    }


@users_router.post("/connections/{connection_id}/accept", response_model=MessageResponse)
def accept_connection(connection_id: int, current_user: CurrentUser, db: Database) -> MessageResponse:
    connection = db.get(Connection, connection_id)
    if connection is None or current_user.id not in (connection.user_low_id, connection.user_high_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection request not found")
    if connection.requester_id == current_user.id or connection.status != ConnectionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This request cannot be accepted")
    connection.status = ConnectionStatus.ACCEPTED
    db.commit()
    return MessageResponse(message="Connection accepted")


@users_router.post("/connections/{connection_id}/decline", response_model=MessageResponse)
def decline_connection(connection_id: int, current_user: CurrentUser, db: Database) -> MessageResponse:
    connection = db.get(Connection, connection_id)
    if connection is None or current_user.id not in (connection.user_low_id, connection.user_high_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection request not found")
    if connection.requester_id == current_user.id or connection.status != ConnectionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This request cannot be declined")
    connection.status = ConnectionStatus.DECLINED
    db.commit()
    return MessageResponse(message="Connection declined")


@users_router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_connection(connection_id: int, current_user: CurrentUser, db: Database) -> Response:
    connection = db.get(Connection, connection_id)
    if connection is None or current_user.id not in (connection.user_low_id, connection.user_high_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    db.delete(connection)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_accessible_event(db: Session, user_id: int, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if event is None or not can_access_event(db, user_id, event):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@events_router.post("", response_model=EventView, status_code=status.HTTP_201_CREATED)
def post_event(payload: EventInput, current_user: CurrentUser, db: Database):
    try:
        event = create_event(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None
    return event_view(db, event, current_user.id)


@events_router.get("/invitations", response_model=list[EventView])
def get_invitations(current_user: CurrentUser, db: Database):
    events = db.scalars(
        select(Event).join(EventInvitation, EventInvitation.event_id == Event.id).where(
            EventInvitation.user_id == current_user.id,
            Event.status == EventStatus.ACTIVE,
            Event.ends_at > datetime.now(UTC),
        ).order_by(Event.starts_at).limit(100)
    ).all()
    return [event_view(db, event, current_user.id) for event in events]


@events_router.get("/{event_id}", response_model=EventView)
def get_event(event_id: int, current_user: CurrentUser, db: Database):
    return event_view(db, _get_accessible_event(db, current_user.id, event_id), current_user.id)


@events_router.patch("/{event_id}", response_model=EventView)
def patch_event(event_id: int, payload: EventInput, current_user: CurrentUser, db: Database):
    event = db.get(Event, event_id)
    if event is None or event.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.status != EventStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled events cannot be edited")
    if payload.invite_user_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invitations cannot be changed when editing an event")
    updated = update_event(db, event, payload)
    return event_view(db, updated, current_user.id)


@events_router.post("/{event_id}/cancel", response_model=MessageResponse)
def cancel_event(event_id: int, current_user: CurrentUser, db: Database):
    event = db.get(Event, event_id)
    if event is None or event.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    event.status = EventStatus.CANCELLED
    event.updated_at = datetime.now(UTC)
    db.commit()
    return MessageResponse(message="Event cancelled")


@events_router.post("/{event_id}/join", response_model=EventView)
def join_event(event_id: int, current_user: CurrentUser, db: Database):
    event = _get_accessible_event(db, current_user.id, event_id)
    if event.status != EventStatus.ACTIVE or utc_datetime(event.ends_at) <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This event is no longer active")
    participant = db.scalar(select(Participant).where(
        Participant.event_id == event.id,
        Participant.user_id == current_user.id,
    ))
    if participant is not None and participant.status == ParticipantStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already joined this event")
    if participant is None:
        participant = Participant(
            event_id=event.id,
            user_id=current_user.id,
            status=ParticipantStatus.ACTIVE,
            joined_at=datetime.now(UTC),
        )
        db.add(participant)
    else:
        participant.status = ParticipantStatus.ACTIVE
        participant.joined_at = datetime.now(UTC)
        participant.left_at = None
    invitation = db.scalar(select(EventInvitation).where(
        EventInvitation.event_id == event.id,
        EventInvitation.user_id == current_user.id,
    ))
    if invitation is not None:
        db.delete(invitation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already joined this event") from None
    return event_view(db, event, current_user.id)


@events_router.post("/{event_id}/leave", response_model=MessageResponse)
def leave_event_route(event_id: int, current_user: CurrentUser, db: Database):
    event = _get_accessible_event(db, current_user.id, event_id)
    leave_event(db, event, current_user)
    return MessageResponse(message="You left the event")


@calendar_router.get("", response_model=list[EventView])
def get_calendar(
    current_user: CurrentUser,
    db: Database,
    view: str = Query(pattern="^(mine|circle)$"),
    starts_at: datetime = Query(),
    ends_at: datetime = Query(),
):
    if starts_at.tzinfo is None or ends_at.tzinfo is None or ends_at <= starts_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid timezone-aware date range is required")
    if ends_at - starts_at > timedelta(days=31):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Calendar ranges cannot exceed 31 days")
    events = db.scalars(visible_events_query(db, current_user.id, view, starts_at.astimezone(UTC), ends_at.astimezone(UTC))).all()
    return [event_view(db, event, current_user.id) for event in events]


@notifications_router.get("", response_model=list[NotificationView])
def list_notifications(current_user: CurrentUser, db: Database):
    notifications = db.scalars(
        select(Notification).where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc()).limit(100)
    ).all()
    results = []
    for notification in notifications:
        actor = db.get(User, notification.actor_id)
        event = db.get(Event, notification.event_id)
        has_access = event is not None and can_access_event(db, current_user.id, event)
        title = event.title if has_access else None
        results.append({
            "id": notification.id,
            "actor_nickname": actor.nickname if actor else "A connection",
            "event_id": notification.event_id if has_access else None,
            "event_title": title,
            "read": notification.read,
            "created_at": notification.created_at,
            "message": f"{actor.nickname if actor else 'A connection'} left {title}" if title else f"{actor.nickname if actor else 'A connection'} left an event you can no longer view.",
        })
    return results


@notifications_router.get("/unread-count")
def unread_count(current_user: CurrentUser, db: Database) -> dict[str, int]:
    count = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.recipient_id == current_user.id,
        Notification.read.is_(False),
    ))
    return {"count": int(count or 0)}


@notifications_router.post("/{notification_id}/read", response_model=MessageResponse)
def mark_notification_read(notification_id: int, current_user: CurrentUser, db: Database):
    notification = db.get(Notification, notification_id)
    if notification is None or notification.recipient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.read = True
    db.commit()
    return MessageResponse(message="Notification marked as read")


router.include_router(auth_router)
router.include_router(users_router)
router.include_router(events_router)
router.include_router(calendar_router)
router.include_router(notifications_router)
