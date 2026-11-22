import pytest

from app.models.enums import EventStatus, UserRole

API = "/api/v1"


def apply(client, headers):
    return client.post(
        f"{API}/organisers/apply", json={"organisation_name": "Test Events"}, headers=headers
    )


def decide(client, headers, application_id, status):
    return client.patch(
        f"{API}/admin/organisers/{application_id}", json={"status": status}, headers=headers
    )


def reserve(client, headers, tier_id, quantity=1):
    return client.post(
        f"{API}/orders", json={"tier_id": tier_id, "quantity": quantity}, headers=headers
    )


def buy(client, headers, tier_id, quantity=1):
    order = reserve(client, headers, tier_id, quantity).json()
    return client.post(f"{API}/orders/{order['id']}/pay", headers=headers).json()


def event_payload():
    return {
        "title": "Lagos Live 2027",
        "description": "A night of live music.",
        "venue": "Eko Convention Centre",
        "city": "Lagos",
        "category": "music",
        "starts_at": "2027-03-20T18:00:00Z",
        "ends_at": "2027-03-20T23:59:00Z",
    }


def test_admin_lists_applications_oldest_first_and_filters_by_status(client, auth, make_user):
    admin = make_user(UserRole.ADMIN)
    first_id = apply(client, auth(make_user())).json()["id"]
    second_id = apply(client, auth(make_user())).json()["id"]
    assert decide(client, auth(admin), first_id, "approved").status_code == 200

    everything = client.get(f"{API}/admin/organisers", headers=auth(admin)).json()
    pending = client.get(
        f"{API}/admin/organisers", params={"status": "pending"}, headers=auth(admin)
    ).json()
    bad_filter = client.get(
        f"{API}/admin/organisers", params={"status": "banana"}, headers=auth(admin)
    )

    assert everything["total"] == 2
    assert [item["id"] for item in everything["items"]] == [first_id, second_id]
    assert pending["total"] == 1
    assert pending["items"][0]["id"] == second_id
    assert bad_filter.status_code == 422


def test_approving_turns_the_applicant_into_an_organiser_at_once(client, auth, make_user):
    admin = make_user(UserRole.ADMIN)
    headers = auth(make_user())
    application = apply(client, headers).json()
    assert client.post(f"{API}/events", json=event_payload(), headers=headers).status_code == 403

    response = decide(client, auth(admin), application["id"], "approved")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["reviewed_by"] == admin.id
    assert client.post(f"{API}/events", json=event_payload(), headers=headers).status_code == 201


def test_a_decision_is_final(client, auth, make_user):
    admin = make_user(UserRole.ADMIN)
    application = apply(client, auth(make_user())).json()
    assert decide(client, auth(admin), application["id"], "approved").status_code == 200

    second = decide(client, auth(admin), application["id"], "rejected")

    assert second.status_code == 409
    assert second.json()["detail"] == "This application has already been reviewed"


def test_rejecting_leaves_the_applicant_an_attendee(client, auth, make_user):
    admin = make_user(UserRole.ADMIN)
    headers = auth(make_user())
    application = apply(client, headers).json()

    assert decide(client, auth(admin), application["id"], "rejected").status_code == 200

    me = client.get(f"{API}/auth/me", headers=headers)
    assert me.json()["role"] == "attendee"


def test_deciding_on_an_unknown_application_returns_404(client, auth, make_user):
    admin = make_user(UserRole.ADMIN)

    assert decide(client, auth(admin), 999999, "approved").status_code == 404


def test_pending_is_not_a_valid_decision(client, auth, make_user):
    admin = make_user(UserRole.ADMIN)
    application = apply(client, auth(make_user())).json()

    assert decide(client, auth(admin), application["id"], "pending").status_code == 422


ADMIN_ONLY = [
    ("GET", "/admin/organisers", None),
    ("PATCH", "/admin/organisers/1", {"status": "approved"}),
    ("PATCH", "/admin/events/1", {"status": "suspended"}),
    ("GET", "/admin/stats", None),
]


@pytest.mark.parametrize("method, path, body", ADMIN_ONLY)
def test_admin_endpoints_are_for_admins_only(client, auth, make_user, method, path, body):
    url = f"{API}{path}"

    attendee = client.request(method, url, json=body, headers=auth(make_user()))
    organiser = client.request(
        method, url, json=body, headers=auth(make_user(UserRole.ORGANISER))
    )
    visitor = client.request(method, url, json=body)

    assert attendee.status_code == 403
    assert organiser.status_code == 403
    assert visitor.status_code == 401


def test_suspending_hides_an_event_and_restoring_shows_it_again(
    client, auth, make_user, make_event
):
    admin = make_user(UserRole.ADMIN)
    event = make_event(make_user(UserRole.ORGANISER))
    url = f"{API}/admin/events/{event.id}"

    suspended = client.patch(url, json={"status": "suspended"}, headers=auth(admin))

    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"
    assert client.get(f"{API}/events/{event.id}").status_code == 404
    assert client.get(f"{API}/events").json()["items"] == []

    restored = client.patch(url, json={"status": "published"}, headers=auth(admin))

    assert restored.status_code == 200
    assert client.get(f"{API}/events/{event.id}").status_code == 200


def test_only_published_events_can_be_suspended_and_only_suspended_ones_restored(
    client, auth, make_user, make_event
):
    admin = make_user(UserRole.ADMIN)
    organiser = make_user(UserRole.ORGANISER)
    draft = make_event(organiser, status=EventStatus.DRAFT)
    live = make_event(organiser)

    suspend_draft = client.patch(
        f"{API}/admin/events/{draft.id}", json={"status": "suspended"}, headers=auth(admin)
    )
    restore_live = client.patch(
        f"{API}/admin/events/{live.id}", json={"status": "published"}, headers=auth(admin)
    )

    assert suspend_draft.status_code == 409
    assert restore_live.status_code == 409


def test_stats_count_events_and_only_paid_orders(
    client, auth, make_user, make_event, make_tier
):
    admin = make_user(UserRole.ADMIN)
    organiser = make_user(UserRole.ORGANISER)
    event = make_event(organiser)
    make_event(organiser)
    tier = make_tier(event, quantity=10, price_kobo=500000)
    keeper, refunded, waiting = make_user(), make_user(), make_user()
    buy(client, auth(keeper), tier.id, quantity=2)
    order = buy(client, auth(refunded), tier.id)
    refund = client.post(f"{API}/orders/{order['id']}/refund", headers=auth(refunded))
    assert refund.status_code == 200
    assert reserve(client, auth(waiting), tier.id).status_code == 201

    response = client.get(f"{API}/admin/stats", headers=auth(admin))

    assert response.status_code == 200
    assert response.json() == {
        "total_events": 2,
        "tickets_sold": 2,
        "total_revenue_kobo": 1000000,
    }