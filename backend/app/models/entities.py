from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EventCategory(StrEnum):
    SPORTS = "sports"
    FOOD = "food"
    ART = "art"
    SOCIAL = "social"


class EventStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class ConnectionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ParticipantStatus(StrEnum):
    ACTIVE = "active"
    LEFT = "left"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(40), index=True)
    gender: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Connection(Base):
    __tablename__ = "connections"
    __table_args__ = (
        CheckConstraint("user_low_id < user_high_id", name="ck_connection_canonical_order"),
        UniqueConstraint("user_low_id", "user_high_id", name="uq_connection_pair"),
        Index("ix_connections_status_low", "status", "user_low_id"),
        Index("ix_connections_status_high", "status", "user_high_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_low_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user_high_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[ConnectionStatus] = mapped_column(Enum(ConnectionStatus, name="connection_status"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_event_end_after_start"),
        Index("ix_events_active_start", "status", "starts_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(2000), default="")
    category: Mapped[EventCategory] = mapped_column(Enum(EventCategory, name="event_category"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str] = mapped_column(String(200))
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus, name="event_status"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_participant"),
        Index("ix_participants_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[ParticipantStatus] = mapped_column(Enum(ParticipantStatus, name="participant_status"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EventInvitation(Base):
    __tablename__ = "event_invitations"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_invitation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    invited_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("leave_action_id", "recipient_id", name="uq_leave_notification"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    leave_action_id: Mapped[str] = mapped_column(String(36), nullable=False)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
