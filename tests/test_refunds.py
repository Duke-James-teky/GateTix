from datetime import timedelta

import pytest

from app.models.enums import OrderStatus, UserRole
from app.models.order import Order

API = "/api/v1"


def reserve(client, headers, tier_id, quantity=1):
    return client.post(
        f"{API}/orders",
        json={"tier_id": tier_id, "quantity": quantity},
        headers=headers,
    )


def pay(client, headers, order_id):
    return client.post(f"{API}/orders/{order_id}/pay", headers=headers)


def refund(client, headers, order_id):
    return client.post(f"{API}/orders/{order_id}/refund", headers=headers)


def buy(client, headers, tier_id, quantity=1):
    order = reserve(client, headers, tier_id, quantity).json()
    return pay(client, headers, order["id"]).json()


@pytest.fixture
def organiser(make_user):
    return make_user(UserRole.ORGANISER)


def test_a_refund_voids_the_tickets_and_returns_the_seats(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=10)
    buyer = make_user()
    order = buy(client, auth(buyer), tier.id, quantity=2)

    response = refund(client, auth(buyer), order["id"])

    assert response.status_code == 200
    assert response.json()["status"] == "refunded"
    tickets = client.get(f"{API}/tickets", headers=auth(buyer)).json()["items"]
    assert {ticket["status"] for ticket in tickets} == {"refunded"}
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (0, 0)


def test_a_refunded_order_cannot_be_refunded_again(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser))
    buyer = make_user()
    order = buy(client, auth(buyer), tier.id)
    assert refund(client, auth(buyer), order["id"]).status_code == 200

    second = refund(client, auth(buyer), order["id"])

    assert second.status_code == 409
    assert second.json()["detail"] == "This order has already been refunded"


def test_only_paid_orders_can_be_refunded(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser))
    buyer = make_user()
    pending = reserve(client, auth(buyer), tier.id).json()

    response = refund(client, auth(buyer), pending["id"])

    assert response.status_code == 409
    assert response.json()["detail"] == "Only paid orders can be refunded"


def test_refunds_close_48_hours_before_the_event(
    client, auth, make_user, make_event, make_tier, organiser
):
    event = make_event(organiser, starts_in=timedelta(hours=24))
    tier = make_tier(event)
    buyer = make_user()
    order = buy(client, auth(buyer), tier.id)

    response = refund(client, auth(buyer), order["id"])

    assert response.status_code == 400
    assert "48 hours" in response.json()["detail"]


def test_a_refund_is_still_allowed_just_outside_the_cutoff(
    client, auth, make_user, make_event, make_tier, organiser
):
    event = make_event(organiser, starts_in=timedelta(hours=49))
    tier = make_tier(event)
    buyer = make_user()
    order = buy(client, auth(buyer), tier.id)

    response = refund(client, auth(buyer), order["id"])

    assert response.status_code == 200


def test_nobody_else_can_refund_my_order(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser))
    owner, stranger = make_user(), make_user()
    order = buy(client, auth(owner), tier.id)

    response = refund(client, auth(stranger), order["id"])

    assert response.status_code == 403


def test_refunded_seats_can_be_bought_again(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=2, max_per_order=2)
    first, second = make_user(), make_user()
    order = buy(client, auth(first), tier.id, quantity=2)
    assert reserve(client, auth(second), tier.id).status_code == 409

    assert refund(client, auth(first), order["id"]).status_code == 200

    assert reserve(client, auth(second), tier.id).status_code == 201


def test_cancelling_an_event_refunds_paid_orders_and_releases_unpaid_reservations(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    event = make_event(organiser)
    tier = make_tier(event, quantity=10)
    paying, waiting = make_user(), make_user()
    paid = buy(client, auth(paying), tier.id, quantity=2)
    pending = reserve(client, auth(waiting), tier.id).json()

    response = client.post(f"{API}/events/{event.id}/cancel", headers=auth(organiser))

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    db.expire_all()
    assert db.get(Order, paid["id"]).status == OrderStatus.REFUNDED
    assert db.get(Order, pending["id"]).status == OrderStatus.EXPIRED
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (0, 0)
    assert client.get(f"{API}/events/{event.id}").status_code == 404
    assert reserve(client, auth(waiting), tier.id).status_code == 404


def test_only_the_owning_organiser_can_cancel_an_event(
    client, auth, make_user, make_event, organiser
):
    event = make_event(organiser)
    other_organiser = make_user(UserRole.ORGANISER)
    cancel = f"{API}/events/{event.id}/cancel"

    assert client.post(cancel, headers=auth(other_organiser)).status_code == 403
    assert client.post(cancel, headers=auth(make_user())).status_code == 403
    assert client.post(cancel).status_code == 401


def test_cancelling_an_event_twice_is_refused(client, auth, make_event, organiser):
    event = make_event(organiser)
    cancel = f"{API}/events/{event.id}/cancel"
    assert client.post(cancel, headers=auth(organiser)).status_code == 200

    second = client.post(cancel, headers=auth(organiser))

    assert second.status_code == 409
    assert second.json()["detail"] == "This event is already cancelled"