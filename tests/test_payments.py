import pytest
from sqlalchemy import func, select

from app.models.enums import EventStatus, OrderStatus, UserRole
from app.models.order import Order
from app.models.ticket import Ticket

API = "/api/v1"


def reserve(client, headers, tier_id, quantity=1):
    return client.post(
        f"{API}/orders",
        json={"tier_id": tier_id, "quantity": quantity},
        headers=headers,
    )


def pay(client, headers, order_id):
    return client.post(f"{API}/orders/{order_id}/pay", headers=headers)


@pytest.fixture
def organiser(make_user):
    return make_user(UserRole.ORGANISER)


def test_paying_issues_one_unique_ticket_per_seat(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=10)
    buyer = make_user()
    order = reserve(client, auth(buyer), tier.id, quantity=3).json()

    response = pay(client, auth(buyer), order["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paid"
    tickets = body["tickets"]
    assert len(tickets) == 3
    assert {ticket["status"] for ticket in tickets} == {"valid"}
    codes = {ticket["code"] for ticket in tickets}
    assert len(codes) == 3
    assert all(len(code) >= 20 for code in codes)
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (3, 0)


def test_paying_twice_is_refused_and_issues_no_extra_tickets(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser))
    buyer = make_user()
    order = reserve(client, auth(buyer), tier.id, quantity=3).json()
    assert pay(client, auth(buyer), order["id"]).status_code == 200

    second = pay(client, auth(buyer), order["id"])

    assert second.status_code == 409
    assert second.json()["detail"] == "This order has already been paid"
    count = db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.order_id == order["id"])
    )
    assert count == 3


def test_nobody_else_can_pay_for_my_order(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser))
    owner, stranger = make_user(), make_user()
    order = reserve(client, auth(owner), tier.id).json()

    response = pay(client, auth(stranger), order["id"])

    assert response.status_code == 403
    db.expire_all()
    assert db.get(Order, order["id"]).status == OrderStatus.PENDING


def test_paying_an_order_that_does_not_exist_returns_404(client, auth, make_user):
    response = pay(client, auth(make_user()), 999999)

    assert response.status_code == 404


def test_paying_is_refused_while_the_event_is_suspended(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    event = make_event(organiser)
    tier = make_tier(event)
    buyer = make_user()
    order = reserve(client, auth(buyer), tier.id).json()
    event.status = EventStatus.SUSPENDED
    db.commit()

    response = pay(client, auth(buyer), order["id"])

    assert response.status_code == 409
    assert response.json()["detail"] == "This event is not currently on sale"