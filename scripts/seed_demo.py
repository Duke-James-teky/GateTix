"""Create the demo accounts and a demo event. Safe to run more than once.

Run from the project root:  python -m scripts.seed_demo
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.enums import EventStatus, UserRole
from app.models.event import Event
from app.models.ticket_tier import TicketTier
from app.models.user import User

DEMO_PASSWORD = "DemoPass123"
DEMO_USERS = [
    ("Demo Attendee", "demo.attendee@example.com", UserRole.ATTENDEE),
    ("Demo Organiser", "demo.organiser@example.com", UserRole.ORGANISER),
    ("Demo Admin", "demo.admin@example.com", UserRole.ADMIN),
]
EVENT_TITLE = "Lagos Live (Demo Event)"


def get_or_create_user(db: Session, name: str, email: str, role: UserRole) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        print(f"exists   {role.value:<9} {email}")
        return user

    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(DEMO_PASSWORD),
        role=role,
    )
    db.add(user)
    db.flush()
    print(f"created  {role.value:<9} {email}")
    return user


def seed_event(db: Session, organiser: User) -> None:
    already_there = db.scalar(
        select(Event.id).where(
            Event.organiser_id == organiser.id, Event.title == EVENT_TITLE
        )
    )
    if already_there is not None:
        print(f"exists   event     {EVENT_TITLE}")
        return

    now = datetime.now(timezone.utc)
    starts_at = now + timedelta(days=60)
    event = Event(
        organiser_id=organiser.id,
        title=EVENT_TITLE,
        description="A night of live music. Created by the seed script for demos.",
        venue="Eko Convention Centre",
        city="Lagos",
        category="music",
        status=EventStatus.PUBLISHED,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
    )
    db.add(event)
    db.flush()

    tiers = [
        ("Regular", 500_000, 100, 4),
        ("VIP", 1_500_000, 20, 2),
        ("Free Standing", 0, 30, 2),
    ]
    for name, price_kobo, quantity, max_per_order in tiers:
        db.add(
            TicketTier(
                event_id=event.id,
                name=name,
                price_kobo=price_kobo,
                quantity=quantity,
                sales_start=now - timedelta(days=1),
                sales_end=starts_at - timedelta(hours=1),
                max_per_order=max_per_order,
            )
        )
    print(f"created  event     {EVENT_TITLE} with {len(tiers)} tiers")


def main() -> None:
    db = SessionLocal()
    try:
        users = {
            role: get_or_create_user(db, name, email, role)
            for name, email, role in DEMO_USERS
        }
        seed_event(db, users[UserRole.ORGANISER])
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()