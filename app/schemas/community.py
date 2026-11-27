
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommunityCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=5000)
    is_public: bool = True


class CommunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organiser_id: int
    title: str
    description: str
    is_public: bool
    created_at: datetime


class CommunityUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    is_public: bool | None = None


class AnnouncementCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=180)
    body: str = Field(min_length=1, max_length=10000)
    series_id: int | None = None


class AnnouncementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organiser_id: int
    series_id: int | None
    title: str
    body: str
    published_at: datetime | None
    created_at: datetime


class InvitationCreate(BaseModel):
    invitee_id: int = Field(gt=0)


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    inviter_id: int
    invitee_id: int
    created_at: datetime


class FollowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    follower_id: int
    organiser_id: int
    created_at: datetime
