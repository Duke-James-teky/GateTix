from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import EventStatus, OrderStatus, TicketStatus, UserRole
from app.models.order import Order
from app.models.ticket import Ticket
from app.utils.ticket_codes import generate_ticket_code

API = "/api/v1"


def check_in(client, headers, event_id, code):
    return client.post(
        f"{API}/events/{event_id}/check-in", json={"code": code}, headers=headers
    )


def make_paid_order(db, event, tier, attendee, quantity=1):
    """Create a paid order with its tickets, as if the attendee had already bought them."""
    order = Order(
        attendee_id=attendee.id,
        tier_id=tier.id,
        event_id=event.id,
        quantity=quantity,
        total_kobo=tier.price_kobo * quantity,
        status=OrderStatus.PAID,
    )
    db.add(order)
    db.flush()
    tickets = [Ticket(order_id=order.id, code=generate_ticket_code()) for _ in range(quantity)]
    db.add_all(tickets)
    tier.sold += quantity
    db.commit()
    return order, tickets


@pytest.fixture
def gate(db, make_user, make_event, make_tier):
    """An organiser and an event that is under way, so today's check-in window is open."""
    organiser = make_user(UserRole.ORGANISER)
    now = datetime.now(timezone.utc)
    event = make_event(
        organiser, starts_at=now - timedelta(hours=1), ends_at=now + timedelta(hours=2)
    )
    tier = make_tier(event)
    return organiser, event, tier


def test_an_organiser_checks_in_a_valid_ticket(client, db, auth, make_user, gate):
    organiser, event, tier = gate
    _, tickets = make_paid_order(db, event, tier, make_user())

    response = check_in(client, auth(organiser), event.id, tickets[0].code)

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Ticket checked in"
    assert body["ticket"]["status"] == "used"
    assert body["ticket"]["checked_in_at"] is not None


def test_a_second_scan_of_the_same_code_is_rejected(client, db, auth, make_user, gate):
    organiser, event, tier = gate
    _, tickets = make_paid_order(db, event, tier, make_user())
    assert check_in(client, auth(organiser), event.id, tickets[0].code).status_code == 200

    second = check_in(client, auth(organiser), event.id, tickets[0].code)

    assert second.status_code == 409
    assert second.json()["detail"] == "This ticket has already been used"


def test_an_unknown_code_is_not_found(client, auth, gate):
    organiser, event, _ = gate

    response = check_in(client, auth(organiser), event.id, "x" * 22)

    assert response.status_code == 404


def test_refunded_tickets_never_check_in(client, db, auth, make_user, gate):
    organiser, event, tier = gate
    _, tickets = make_paid_order(db, event, tier, make_user())
    tickets[0].status = TicketStatus.REFUNDED
    db.commit()

    response = check_in(client, auth(organiser), event.id, tickets[0].code)

    assert response.status_code == 409
    assert response.json()["detail"] == "This ticket is no longer valid"


def test_a_ticket_from_another_event_is_not_found(
    client, db, auth, make_user, make_event, make_tier, gate
):
    organiser, event, _ = gate
    now = datetime.now(timezone.utc)
    other_event = make_event(
        organiser, starts_at=now - timedelta(hours=1), ends_at=now + timedelta(hours=2)
    )
    other_tier = make_tier(other_event)
    _, tickets = make_paid_order(db, other_event, other_tier, make_user())

    response = check_in(client, auth(organiser), event.id, tickets[0].code)

    assert response.status_code == 404


def test_only_the_owning_organiser_can_check_in(client, db, auth, make_user, gate):
    organiser, event, tier = gate
    _, tickets = make_paid_order(db, event, tier, make_user())
    other_organiser = make_user(UserRole.ORGANISER)
    code = tickets[0].code

    assert check_in(client, auth(other_organiser), event.id, code).status_code == 403
    assert check_in(client, auth(make_user()), event.id, code).status_code == 403
    assert check_in(client, {}, event.id, code).status_code == 401


def test_check_in_is_only_open_on_the_day_of_the_event(
    client, db, auth, make_user, make_event, make_tier
):
    organiser = make_user(UserRole.ORGANISER)
    event = make_event(organiser, starts_in=timedelta(days=30))
    tier = make_tier(event)
    _, tickets = make_paid_order(db, event, tier, make_user())

    response = check_in(client, auth(organiser), event.id, tickets[0].code)

    assert response.status_code == 400
    assert response.json()["detail"] == "Check-in is only open on the day of the event"


def test_check_in_is_closed_for_events_that_are_not_published(
    client, db, auth, make_user, gate
):
    organiser, event, tier = gate
    _, tickets = make_paid_order(db, event, tier, make_user())
    event.status = EventStatus.SUSPENDED
    db.commit()

    response = check_in(client, auth(organiser), event.id, tickets[0].code)

    assert response.status_code == 409
    assert "published" in response.json()["detail"]


def test_the_sales_report_counts_sold_checked_in_and_revenue(
    client, db, auth, make_user, gate
):
    organiser, event, tier = gate
    make_paid_order(db, event, tier, make_user(), quantity=3)
    _, second = make_paid_order(db, event, tier, make_user(), quantity=2)
    assert check_in(client, auth(organiser), event.id, second[0].code).status_code == 200

    response = client.get(f"{API}/events/{event.id}/report", headers=auth(organiser))

    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == event.id
    row = body["tiers"][0]
    assert (row["name"], row["sold"], row["remaining"], row["checked_in"]) == ("Regular", 5, 5, 1)
    assert row["revenue_kobo"] == 5 * tier.price_kobo
    assert body["total_sold"] == 5
    assert body["total_checked_in"] == 1
    assert body["total_revenue_kobo"] == 5 * tier.price_kobo


def test_only_the_owning_organiser_can_see_the_report(client, auth, make_user, gate):
    _, event, _ = gate
    report = f"{API}/events/{event.id}/report"

    assert client.get(report, headers=auth(make_user(UserRole.ORGANISER))).status_code == 403
    assert client.get(report, headers=auth(make_user())).status_code == 403
    assert client.get(report).status_code == 401