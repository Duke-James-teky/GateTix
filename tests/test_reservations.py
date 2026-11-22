from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import EventStatus, UserRole

API = "/api/v1"


def reserve(client, headers, tier_id, quantity=1):
    return client.post(
        f"{API}/orders",
        json={"tier_id": tier_id, "quantity": quantity},
        headers=headers,
    )


@pytest.fixture
def organiser(make_user):
    return make_user(UserRole.ORGANISER)


def test_reserve_holds_the_tickets_for_ten_minutes(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser))
    buyer = make_user()
    before = datetime.now(timezone.utc)

    response = reserve(client, auth(buyer), tier.id, quantity=2)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["quantity"] == 2
    assert body["total_kobo"] == 2 * tier.price_kobo
    held_for = datetime.fromisoformat(body["expires_at"]) - before
    assert timedelta(minutes=9) < held_for < timedelta(minutes=11)
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (0, 2)


def test_reserve_rejects_more_than_the_max_per_order(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), max_per_order=4)

    response = reserve(client, auth(make_user()), tier.id, quantity=5)

    assert response.status_code == 400
    assert "at most 4 tickets" in response.json()["detail"]


@pytest.mark.parametrize("window", ["not_started", "ended"])
def test_reserve_rejects_outside_the_sales_window(
    client, auth, make_user, make_event, make_tier, organiser, window
):
    now = datetime.now(timezone.utc)
    if window == "not_started":
        dates = dict(sales_start=now + timedelta(days=1), sales_end=now + timedelta(days=5))
    else:
        dates = dict(sales_start=now - timedelta(days=5), sales_end=now - timedelta(days=1))
    tier = make_tier(make_event(organiser), **dates)

    response = reserve(client, auth(make_user()), tier.id)

    assert response.status_code == 400


def test_reserve_rejects_an_event_that_has_already_started(
    client, auth, make_user, make_event, make_tier, organiser
):
    event = make_event(organiser, starts_in=timedelta(hours=-1))
    tier = make_tier(event)

    response = reserve(client, auth(make_user()), tier.id)

    assert response.status_code == 400
    assert response.json()["detail"] == "This event has already started"


def test_reserve_refuses_events_that_are_not_published(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser, status=EventStatus.DRAFT))

    response = reserve(client, auth(make_user()), tier.id)

    assert response.status_code == 404


def test_an_attendee_can_hold_only_one_pending_reservation_per_event(
    client, auth, make_user, make_event, make_tier, organiser
):
    event = make_event(organiser)
    regular = make_tier(event, name="Regular")
    vip = make_tier(event, name="VIP")
    buyer = make_user()

    assert reserve(client, auth(buyer), regular.id).status_code == 201
    second = reserve(client, auth(buyer), vip.id)

    assert second.status_code == 409
    assert "pending reservation" in second.json()["detail"]


def test_reserve_cannot_exceed_what_is_left(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=3, max_per_order=3)
    first, second, third = make_user(), make_user(), make_user()

    assert reserve(client, auth(first), tier.id, quantity=2).status_code == 201

    too_many = reserve(client, auth(second), tier.id, quantity=2)
    assert too_many.status_code == 409
    assert too_many.json()["detail"] == "Only 1 ticket left"

    assert reserve(client, auth(second), tier.id, quantity=1).status_code == 201

    sold_out = reserve(client, auth(third), tier.id, quantity=1)
    assert sold_out.status_code == 409
    assert sold_out.json()["detail"] == "Sold out"


def test_free_tier_orders_are_paid_immediately_with_their_tickets(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), price_kobo=0)

    response = reserve(client, auth(make_user()), tier.id, quantity=2)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "paid"
    assert body["total_kobo"] == 0
    assert len(body["tickets"]) == 2
    assert len({ticket["code"] for ticket in body["tickets"]}) == 2
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (2, 0)


def test_only_attendees_and_organisers_can_reserve(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser))
    admin = make_user(UserRole.ADMIN)

    assert reserve(client, auth(admin), tier.id).status_code == 403
    assert reserve(client, {}, tier.id).status_code == 401