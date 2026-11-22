import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent

# Point the whole app at the TEST database before anything imports it.
_env = {**dotenv_values(ROOT / ".env"), **os.environ}
_test_url = _env.get("TEST_DATABASE_URL")
if not _test_url:
    raise RuntimeError("TEST_DATABASE_URL is not set. Add it to .env.")
if _test_url == _env.get("DATABASE_URL"):
    raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL: tests wipe their database.")
if "test" not in _test_url.rsplit("/", 1)[-1]:
    raise RuntimeError("The test database name must contain 'test'. Refusing to wipe it.")
os.environ["DATABASE_URL"] = _test_url

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import EventStatus, UserRole  # noqa: E402
from app.models.event import Event  # noqa: E402
from app.models.ticket_tier import TicketTier  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    """Build the test database from scratch with the real Alembic migrations."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(database):
    """Empty every table before each test, so tests never affect each other."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE tickets, orders, ticket_tiers, organiser_applications, "
                "events, users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def make_user(db):
    def _make(role=UserRole.ATTENDEE, email=None, name="Test User", password="Password123"):
        user = User(
            name=name,
            email=email or f"{role.value}-{uuid4().hex[:8]}@example.com",
            hashed_password=hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def auth():
    def _auth(user):
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return _auth


@pytest.fixture
def make_event(db):
    def _make(organiser, status=EventStatus.PUBLISHED, starts_in=timedelta(days=30), **overrides):
        start = datetime.now(timezone.utc) + starts_in
        values = dict(
            organiser_id=organiser.id,
            title="Test Event",
            description="A test event",
            venue="Test Hall",
            city="Lagos",
            category="music",
            status=status,
            starts_at=start,
            ends_at=start + timedelta(hours=3),
        )
        values.update(overrides)
        event = Event(**values)
        db.add(event)
        db.commit()
        return event

    return _make


@pytest.fixture
def make_tier(db):
    def _make(event, name="Regular", price_kobo=500000, quantity=10, max_per_order=4, **overrides):
        now = datetime.now(timezone.utc)
        values = dict(
            event_id=event.id,
            name=name,
            price_kobo=price_kobo,
            quantity=quantity,
            sales_start=now - timedelta(days=1),
            sales_end=now + timedelta(days=60),
            max_per_order=max_per_order,
        )
        values.update(overrides)
        tier = TicketTier(**values)
        db.add(tier)
        db.commit()
        return tier

    return _make