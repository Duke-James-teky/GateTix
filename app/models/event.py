from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.enums import EventStatus, enum_column_type

if TYPE_CHECKING:
    from app.models.ticket_tier import TicketTier
class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("ends_at" > "starts_at", name="event_ends_after_starts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organiser_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(text)
    venue: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[EventStatus] = mapped_column(
        enum_column_type(EventStatus, "event_status"),
        default=EventStatus.DRAFT,
        server_default=EventStatus.DRAFT.value,
        index=True,
    )

    tiers: Mapped[list["TicketTier"]] = relationship(order_by="Ticket.id")
