from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import OrderStatus, enum_column_type

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_quantity_positive"),
        CheckConstraint("total_kobo >= 0", name="ck_order_total_not_negative"),
        CheckConstraint(
            "status <> 'pending' OR expires_at IS NOT NULL",
            name="ck_order_pending_has_expiry",
        ),
        Index(
            "uq_one_pending_order_per_attendee_event",
            "attendee_id",
            "event_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_orders_pending_expiry",
            "expires_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attendee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tier_id: Mapped[int] = mapped_column(ForeignKey("ticket_tiers.id"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    quantity: Mapped[int]
    total_kobo: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[OrderStatus] = mapped_column(
        enum_column_type(OrderStatus, "order_status"),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tickets: Mapped[list["Ticket"]] = relationship(order_by="Ticket.id")