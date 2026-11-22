from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketStatus


class TicketRead(BaseModel):
    """A single ticket as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[1])
    order_id: int = Field(examples=[7])
    code: str = Field(
        description="Unique, unguessable code the gate scans.",
        examples=["kQ3vX9sT2mLwP8aZrB1eYg"],
    )
    status: TicketStatus = Field(examples=["valid"])
    checked_in_at: datetime | None = Field(
        default=None,
        description="When the ticket was scanned at the gate. Null until then.",
        examples=[None],
    )


class CheckInRequest(BaseModel):
    """Data the organiser's staff send to check a ticket in."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(min_length=8, max_length=64, examples=["kQ3vX9sT2mLwP8aZrB1eYg"])


class CheckInResponse(BaseModel):
    """Result of a successful check-in."""

    message: str = Field(examples=["Ticket checked in"])
    ticket: TicketRead