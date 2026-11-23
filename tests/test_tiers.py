import pytest

from app.models.enums import EventStatus, UserRole

API = "/api/v1"


def tier_payload(**overrides):
    payload = {
        "name": "VIP",
        "price_kobo": 900000,
        "quantity": 50,
        "sales_start": "2026-11-20T00:00:00Z",
        "sales_end": "2027-03-19T18:00:00Z",
        "max_per_order": 4,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def organiser(make_user):
    return make_user(UserRole.ORGANISER)


def test_an_organiser_adds_a_tier_to_their_event(client, auth, make_event, organiser):
    event = make_event(organiser)

    response = client.post(
        f"{API}/events/{event.id}/tiers", json=tier_payload(), headers=auth(organiser)
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "VIP"
    assert body["price_kobo"] == 900000
    assert (body["sold"], body["reserved"], body["remaining"]) == (0, 0, 50)


def test_tier_names_must_be_unique_within_an_event(client, auth, make_event, organiser):
    event = make_event(organiser)
    url = f"{API}/events/{event.id}/tiers"
    assert client.post(url, json=tier_payload(), headers=auth(organiser)).status_code == 201

    duplicate = client.post(url, json=tier_payload(), headers=auth(organiser))

    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


def test_only_the_owning_organiser_can_add_or_change_tiers(
    client, auth, make_user, make_event, make_tier, organiser
):
    event = make_event(organiser)
    tier = make_tier(event)
    stranger = make_user(UserRole.ORGANISER)
    add_url = f"{API}/events/{event.id}/tiers"
    change_url = f"{API}/tiers/{tier.id}"

    assert client.post(add_url, json=tier_payload(), headers=auth(stranger)).status_code == 403
    assert client.post(add_url, json=tier_payload(), headers=auth(make_user())).status_code == 403
    assert client.post(add_url, json=tier_payload()).status_code == 401
    assert client.patch(change_url, json={"name": "X"}, headers=auth(stranger)).status_code == 403


@pytest.mark.parametrize(
    "overrides",
    [
        {"price_kobo": -1},
        {"quantity": 0},
        {"sales_start": "2027-01-02T00:00:00Z", "sales_end": "2027-01-01T00:00:00Z"},
        {"quantity": 5, "max_per_order": 10},
    ],
    ids=["negative_price", "zero_quantity", "reversed_sales_window", "max_per_order_above_quantity"],
)
def test_a_tier_is_validated(client, auth, make_event, organiser, overrides):
    event = make_event(organiser)

    response = client.post(
        f"{API}/events/{event.id}/tiers", json=tier_payload(**overrides), headers=auth(organiser)
    )

    assert response.status_code == 422


def test_price_and_quantity_can_change_before_any_ticket_sells(
    client, auth, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=10, price_kobo=500000)
    url = f"{API}/tiers/{tier.id}"

    repriced = client.patch(url, json={"price_kobo": 600000}, headers=auth(organiser))
    resized = client.patch(url, json={"quantity": 8}, headers=auth(organiser))

    assert repriced.status_code == 200
    assert repriced.json()["price_kobo"] == 600000
    assert resized.status_code == 200
    assert resized.json()["quantity"] == 8


def test_the_price_is_frozen_once_a_ticket_has_sold(
    client, db, auth, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), price_kobo=500000)
    tier.sold = 1
    db.commit()
    url = f"{API}/tiers/{tier.id}"

    changed = client.patch(url, json={"price_kobo": 700000}, headers=auth(organiser))
    same = client.patch(url, json={"price_kobo": 500000}, headers=auth(organiser))

    assert changed.status_code == 409
    assert changed.json()["detail"] == "Price cannot change after tickets have been sold"
    assert same.status_code == 200


def test_quantity_cannot_drop_below_the_tickets_sold_or_held(
    client, db, auth, make_event, make_tier, organiser
):
    tier = make_tier(make_event(organiser), quantity=10)
    tier.sold = 3
    tier.reserved = 2
    db.commit()
    url = f"{API}/tiers/{tier.id}"

    too_low = client.patch(url, json={"quantity": 4}, headers=auth(organiser))
    exact = client.patch(url, json={"quantity": 5}, headers=auth(organiser))

    assert too_low.status_code == 409
    assert "5 tickets" in too_low.json()["detail"]
    assert exact.status_code == 200


def test_max_per_order_cannot_exceed_the_quantity(client, auth, make_event, make_tier, organiser):
    tier = make_tier(make_event(organiser), quantity=10)

    response = client.patch(
        f"{API}/tiers/{tier.id}", json={"max_per_order": 50}, headers=auth(organiser)
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "max_per_order cannot be greater than quantity"


def test_tiers_cannot_change_on_a_cancelled_event(client, auth, make_event, make_tier, organiser):
    event = make_event(organiser, status=EventStatus.CANCELLED)
    tier = make_tier(event)

    add = client.post(
        f"{API}/events/{event.id}/tiers", json=tier_payload(), headers=auth(organiser)
    )
    change = client.patch(f"{API}/tiers/{tier.id}", json={"name": "New"}, headers=auth(organiser))

    assert add.status_code == 409
    assert change.status_code == 409


def test_changing_a_tier_that_does_not_exist_returns_404(client, auth, organiser):
    response = client.patch(f"{API}/tiers/999999", json={"name": "X"}, headers=auth(organiser))

    assert response.status_code == 404