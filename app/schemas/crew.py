
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CrewRole = Literal[
    "manager",
    "checkin",
    "finance",
    "marketing",
    "support",
]

CrewInvitationStatus = Literal[
    "pending",
    "accepted",
    "rejected",
]


class CrewInviteCreate(BaseModel):
    """Data required to invite a user to an event team."""

    user_id: int = Field(gt=0)
    role: CrewRole = "checkin"


class CrewRoleUpdate(BaseModel):
    """Data required to change a team member's role."""

    role: CrewRole


class CrewInvitationRespond(BaseModel):
    """Data submitted when responding to a team invitation."""

    status: Literal["accepted", "rejected"]


class CrewMemberRead(BaseModel):
    """Team member information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    user_id: int
    role: CrewRole
    status: CrewInvitationStatus
    invited_by: int
    accepted_at: datetime | None = None
    responded_at: datetime | None = None
    created_at: datetime
