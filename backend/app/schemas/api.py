from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationInfo, field_validator, model_validator

from app.models.entities import EventCategory, EventStatus


class RegistrationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: Annotated[str, Field(min_length=10, max_length=128)]
    nickname: Annotated[str, Field(min_length=1, max_length=40)]
    gender: Annotated[str | None, Field(default=None, max_length=40)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("nickname", "gender")
    @classmethod
    def normalize_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        normalized = value.strip() if value is not None else None
        if info.field_name == "nickname" and not normalized:
            raise ValueError("Nickname cannot be blank")
        return normalized or None


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    email: str
    nickname: str
    gender: str | None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserView


class EventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(default="", max_length=2000)]
    category: EventCategory
    starts_at: datetime
    ends_at: datetime
    location: Annotated[str, Field(min_length=1, max_length=200)]
    invite_user_ids: list[int] = Field(default_factory=list, max_length=50)

    @field_validator("title", "description", "location")
    @classmethod
    def normalize_event_text(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip()
        if info.field_name in {"title", "location"} and not normalized:
            raise ValueError(f"{info.field_name.title()} cannot be blank")
        return normalized

    @model_validator(mode="after")
    def check_datetimes(self) -> "EventInput":
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Event datetimes must include a timezone")
        if self.ends_at <= self.starts_at:
            raise ValueError("End time must be later than start time")
        if len(set(self.invite_user_ids)) != len(self.invite_user_ids):
            raise ValueError("Invitations must not contain duplicate users")
        return self


class EventView(BaseModel):
    id: int
    creator_id: int
    title: str
    description: str
    category: EventCategory
    starts_at: datetime
    ends_at: datetime
    location: str
    status: EventStatus
    participant_count: int
    current_user_participating: bool
    current_user_is_creator: bool


class ConnectionRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int


class ConnectionView(BaseModel):
    id: int
    user_id: int
    nickname: str
    status: str
    direction: str


class UserSearchView(BaseModel):
    id: int
    nickname: str


class NotificationView(BaseModel):
    id: int
    actor_nickname: str
    event_id: int | None
    event_title: str | None
    read: bool
    created_at: datetime
    message: str


class CalendarView(StrEnum):
    MINE = "mine"
    CIRCLE = "circle"


class MessageResponse(BaseModel):
    message: str
