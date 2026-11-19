from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import TicketStatus, enum_column_type


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("code", name="uq_ticket_code"),
        CheckConstraint(
            "status <> 'used' OR checked_in_at IS NOT NULL",
            name="ck_ticket_used_has_checkin_time",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    status: Mapped[TicketStatus] = mapped_column(
        enum_column_type(TicketStatus, "ticket_status"),
        default=TicketStatus.VALID,
        server_default=TicketStatus.VALID.value,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )