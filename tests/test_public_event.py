from datetime import datetime, timedelta, timezone

from app.models.enums import UserRole
from app.models.order import Order

API = "/api/v1"


def test_the_public_event_page_counts_expired_reservations_as_available(
    client, db, auth, make_user, make_event, make_tier
):
    event = make_event(make_user(UserRole.ORGANISER))
    tier = make_tier(event, quantity=10)
    order = client.post(
        f"{API}/orders",
        json={"tier_id": tier.id, "quantity": 3},
        headers=auth(make_user()),
    ).json()

    while_held = client.get(f"{API}/events/{event.id}").json()["tiers"][0]["remaining"]
    assert while_held == 7

    stale = db.get(Order, order["id"])
    stale.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    after_expiry = client.get(f"{API}/events/{event.id}").json()["tiers"][0]["remaining"]
    assert after_expiry == 10