from datetime import datetime, timedelta, timezone

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


def expire(db, order_id):
    """Pretend the ten minutes have passed."""
    order = db.get(Order, order_id)
    order.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()


@pytest.fixture
def organiser(make_user):
    return make_user(UserRole.ORGANISER)


def test_an_expired_reservation_is_released_so_the_next_buyer_can_reserve(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=1)
    first_buyer, second_buyer = make_user(), make_user()

    first = reserve(client, auth(first_buyer), tier.id).json()
    assert reserve(client, auth(second_buyer), tier.id).status_code == 409

    expire(db, first["id"])
    second = reserve(client, auth(second_buyer), tier.id)

    assert second.status_code == 201
    db.expire_all()
    assert db.get(Order, first["id"]).status == OrderStatus.EXPIRED
    db.refresh(tier)
    assert tier.reserved == 1


def test_an_expired_reservation_does_not_block_the_same_attendee(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=5)
    buyer = make_user()

    first = reserve(client, auth(buyer), tier.id).json()
    assert reserve(client, auth(buyer), tier.id).status_code == 409

    expire(db, first["id"])

    assert reserve(client, auth(buyer), tier.id).status_code == 201


def test_paying_after_the_time_is_up_is_refused_and_frees_the_seats(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=5)
    buyer = make_user()
    order = reserve(client, auth(buyer), tier.id, quantity=2).json()
    expire(db, order["id"])

    response = client.post(f"{API}/orders/{order['id']}/pay", headers=auth(buyer))

    assert response.status_code == 409
    assert "expired" in response.json()["detail"]
    db.expire_all()
    assert db.get(Order, order["id"]).status == OrderStatus.EXPIRED
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (0, 0)


def test_paying_in_time_turns_the_reservation_into_sold_tickets(
    client, db, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=5)
    buyer = make_user()
    order = reserve(client, auth(buyer), tier.id, quantity=2).json()

    response = client.post(f"{API}/orders/{order['id']}/pay", headers=auth(buyer))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paid"
    assert len(body["tickets"]) == 2
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (2, 0)