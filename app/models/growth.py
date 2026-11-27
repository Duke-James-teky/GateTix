
"""Growth, event operations, community and offline check-in domain models."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base



class EventTeamMember(Base):
    __tablename__ = "event_team_members"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "user_id",
            name="uq_event_team_member",
        ),
        CheckConstraint(
            "role IN ('manager','checkin','finance','marketing','support')",
            name="ck_event_team_role",
        ),
        CheckConstraint(
            "status IN ('pending','accepted','rejected')",
            name="ck_event_team_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="checkin",
        server_default="checkin",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        index=True,
    )

    invited_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

class PromoterLink(Base):
    __tablename__ = "promoter_links"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "code",
            name="uq_promoter_event_code",
        ),
        CheckConstraint(
            "commission_bps >= 0 AND commission_bps <= 10000",
            name="ck_promoter_commission_bps",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )
    promoter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(40))
    commission_bps: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class PromoterAttribution(Base):
    __tablename__ = "promoter_attributions"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_promoter_attribution_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    promoter_link_id: Mapped[int] = mapped_column(
        ForeignKey("promoter_links.id"),
        index=True,
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
    )
    attributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CommissionLedger(Base):
    __tablename__ = "commission_ledger"
    __table_args__ = (
        CheckConstraint(
            "amount_kobo >= 0",
            name="ck_commission_amount_nonnegative",
        ),
        CheckConstraint(
            "status IN ('pending','approved','paid','reversed')",
            name="ck_commission_status",
        ),
        UniqueConstraint("order_id", name="uq_commission_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    promoter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE")
    )
    amount_kobo: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        index=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "tier_id",
            "user_id",
            name="uq_waitlist_user_tier",
        ),
        CheckConstraint(
            "status IN ('waiting','offered','claimed','expired','cancelled')",
            name="ck_waitlist_status",
        ),
        Index(
            "ix_waitlist_queue",
            "event_id",
            "tier_id",
            "status",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )
    tier_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_tiers.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="waiting",
        server_default="waiting",
    )
    offered_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class EventSeries(Base):
    __tablename__ = "event_series"

    id: Mapped[int] = mapped_column(primary_key=True)
    organiser_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default="",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class SeriesEvent(Base):
    __tablename__ = "series_events"
    __table_args__ = (
        UniqueConstraint(
            "series_id",
            "event_id",
            name="uq_series_event",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("event_series.id", ondelete="CASCADE"),
        index=True,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )


class OrganiserFollow(Base):
    __tablename__ = "organiser_follows"
    __table_args__ = (
        UniqueConstraint(
            "follower_id",
            "organiser_id",
            name="uq_organiser_follow",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    organiser_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CommunityAnnouncement(Base):
    __tablename__ = "community_announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    organiser_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    series_id: Mapped[int | None] = mapped_column(
        ForeignKey("event_series.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class EventInvitation(Base):
    __tablename__ = "event_invitations"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "invitee_id",
            name="uq_event_invitee",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )
    inviter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    invitee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class EventAuditLog(Base):
    __tablename__ = "event_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )
    actor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str] = mapped_column(
        Text,
        default="{}",
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CheckinDevice(Base):
    __tablename__ = "checkin_devices"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "device_key_hash",
            name="uq_event_device_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    device_key_hash: Mapped[str] = mapped_column(String(128))
    label: Mapped[str] = mapped_column(
        String(100),
        default="Check-in device",
        server_default="Check-in device",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class OfflineScan(Base):
    __tablename__ = "offline_scans"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "client_scan_id",
            name="uq_device_client_scan",
        ),
        CheckConstraint(
            "result IN ('accepted','duplicate','invalid','conflict')",
            name="ck_offline_scan_result",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("checkin_devices.id", ondelete="CASCADE"),
        index=True,
    )
    ticket_code_hash: Mapped[str] = mapped_column(
        String(128),
        index=True,
    )
    client_scan_id: Mapped[str] = mapped_column(String(80))
    result: Mapped[str] = mapped_column(
        String(20),
        default="accepted",
        server_default="accepted",
    )
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[int | None] = mapped_column(Integer)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
