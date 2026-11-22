import pytest

from app.models.enums import UserRole

API = "/api/v1"


def reserve(client, headers, tier_id, quantity=1):
    return client.post(
        f"{API}/orders",
        json={"tier_id": tier_id, "quantity": quantity},
        headers=headers,
    )


def buy(client, headers, tier_id, quantity=1):
    order = reserve(client, headers, tier_id, quantity).json()
    return client.post(f"{API}/orders/{order['id']}/pay", headers=headers).json()


@pytest.fixture
def organiser(make_user):
    return make_user(UserRole.ORGANISER)


def test_my_tickets_lists_only_my_tickets_with_their_codes(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=10)
    mine, theirs = make_user(), make_user()
    my_order = buy(client, auth(mine), tier.id, quantity=2)
    their_order = buy(client, auth(theirs), tier.id, quantity=1)

    response = client.get(f"{API}/tickets", headers=auth(mine))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    my_codes = {ticket["code"] for ticket in body["items"]}
    assert my_codes == {ticket["code"] for ticket in my_order["tickets"]}
    assert my_codes.isdisjoint({ticket["code"] for ticket in their_order["tickets"]})


def test_my_orders_are_paginated_newest_first(
    client, auth, make_user, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=10)
    buyer = make_user()
    for _ in range(3):
        buy(client, auth(buyer), tier.id)

    first_page = client.get(f"{API}/orders", params={"size": 2}, headers=auth(buyer)).json()
    second_page = client.get(
        f"{API}/orders", params={"size": 2, "page": 2}, headers=auth(buyer)
    ).json()

    assert (first_page["total"], first_page["pages"], first_page["size"]) == (3, 2, 2)
    assert len(first_page["items"]) == 2
    assert first_page["items"][0]["id"] > first_page["items"][1]["id"]
    assert len(second_page["items"]) == 1


def test_order_and_ticket_lists_need_a_buyer_login(client, auth, make_user):
    admin = make_user(UserRole.ADMIN)

    for path in ("orders", "tickets"):
        assert client.get(f"{API}/{path}").status_code == 401
        assert client.get(f"{API}/{path}", headers=auth(admin)).status_code == 403


def test_lists_reject_a_page_size_above_the_maximum(client, auth, make_user):
    headers = auth(make_user())

    assert client.get(f"{API}/orders", params={"size": 1000}, headers=headers).status_code == 422
    assert client.get(f"{API}/tickets", params={"page": 0}, headers=headers).status_code == 422