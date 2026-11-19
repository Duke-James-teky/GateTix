from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class TicketTier(Base):
    __tablename__ = "ticket_tiers"
    __table_args__ = (
        CheckConstraint("sold + reserved <= quantity", name="ck_tier_capacity"),
        CheckConstraint("sold >= 0 AND reserved >= 0", name="ck_tier_counts_not_negative"),
        CheckConstraint("price_kobo >= 0", name="ck_tier_price_not_negative"),
        CheckConstraint("quantity > 0", name="ck_tier_quantity_positive"),
        CheckConstraint("max_per_order > 0", name="ck_tier_max_per_order_positive"),
        CheckConstraint("sales_end > sales_start", name="ck_tier_sales_window"),
        UniqueConstraint("event_id", "name", name="uq_tier_name_per_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    price_kobo: Mapped[int] = mapped_column(BigInteger)
    quantity: Mapped[int]
    sold: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    reserved: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    sales_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sales_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_per_order: Mapped[int]