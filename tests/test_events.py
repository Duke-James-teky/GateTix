from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import EventStatus, UserRole

API = "/api/v1"


def event_payload(**overrides):
    payload = {
        "title": "Lagos Live 2027",
        "description": "A night of live music.",
        "venue": "Eko Convention Centre",
        "city": "Lagos",
        "category": "music",
        "starts_at": "2027-03-20T18:00:00Z",
        "ends_at": "2027-03-20T23:59:00Z",
    }
    payload.update(overrides)
    return payload


def iso(delta):
    """A UTC time, a given distance from now, written the way the API expects."""
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def organiser(make_user):
    return make_user(UserRole.ORGANISER)


def test_an_organiser_creates_a_draft_event(client, auth, organiser):
    response = client.post(f"{API}/events", json=event_payload(), headers=auth(organiser))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["organiser_id"] == organiser.id
    assert body["title"] == "Lagos Live 2027"


def test_attendees_and_visitors_cannot_create_events(client, auth, make_user):
    attendee = client.post(f"{API}/events", json=event_payload(), headers=auth(make_user()))
    visitor = client.post(f"{API}/events", json=event_payload())

    assert attendee.status_code == 403
    assert visitor.status_code == 401


def test_an_event_must_end_after_it_starts(client, auth, organiser):
    payload = event_payload(starts_at="2027-03-20T18:00:00Z", ends_at="2027-03-20T17:00:00Z")

    response = client.post(f"{API}/events", json=payload, headers=auth(organiser))

    assert response.status_code == 422


def test_event_times_must_include_a_timezone(client, auth, organiser):
    payload = event_payload(starts_at="2027-03-20T18:00:00", ends_at="2027-03-20T23:00:00")

    response = client.post(f"{API}/events", json=payload, headers=auth(organiser))

    assert response.status_code == 422


def test_only_the_owning_organiser_can_edit_an_event(
    client, auth, make_user, make_event, organiser
):
    event = make_event(organiser)
    url = f"{API}/events/{event.id}"
    stranger = make_user(UserRole.ORGANISER)

    assert client.patch(url, json={"title": "Hijacked"}, headers=auth(stranger)).status_code == 403
    assert client.patch(url, json={"title": "Hijacked"}, headers=auth(make_user())).status_code == 403
    mine = client.patch(url, json={"title": "Renamed"}, headers=auth(organiser))
    assert mine.status_code == 200
    assert mine.json()["title"] == "Renamed"


def test_a_patch_changes_only_the_fields_that_were_sent(client, auth, make_event, organiser):
    event = make_event(organiser)

    response = client.patch(
        f"{API}/events/{event.id}", json={"city": "Abuja"}, headers=auth(organiser)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Abuja"
    assert body["title"] == "Test Event"
    assert body["venue"] == "Test Hall"


def test_a_patch_checks_the_new_end_time_against_the_stored_start(
    client, auth, make_event, organiser
):
    event = make_event(organiser)

    response = client.patch(
        f"{API}/events/{event.id}",
        json={"ends_at": "2020-01-01T00:00:00Z"},
        headers=auth(organiser),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "ends_at must be after starts_at"


def test_an_empty_patch_is_refused(client, auth, make_event, organiser):
    event = make_event(organiser)

    response = client.patch(f"{API}/events/{event.id}", json={}, headers=auth(organiser))

    assert response.status_code == 400
    assert response.json()["detail"] == "No changes provided"


def test_publishing_needs_at_least_one_tier(client, auth, make_event, make_tier, organiser):
    event = make_event(organiser, status=EventStatus.DRAFT)
    publish = f"{API}/events/{event.id}/publish"

    without_tier = client.post(publish, headers=auth(organiser))
    assert without_tier.status_code == 400
    assert "at least one ticket tier" in without_tier.json()["detail"]

    make_tier(event)
    with_tier = client.post(publish, headers=auth(organiser))
    assert with_tier.status_code == 200
    assert with_tier.json()["status"] == "published"


def test_publishing_twice_is_refused(client, auth, make_event, make_tier, organiser):
    event = make_event(organiser, status=EventStatus.DRAFT)
    make_tier(event)
    publish = f"{API}/events/{event.id}/publish"
    assert client.post(publish, headers=auth(organiser)).status_code == 200

    second = client.post(publish, headers=auth(organiser))

    assert second.status_code == 409
    assert second.json()["detail"] == "Only draft events can be published"


def test_draft_events_are_hidden_from_the_public(client, make_event, organiser):
    draft = make_event(organiser, status=EventStatus.DRAFT)

    assert client.get(f"{API}/events/{draft.id}").status_code == 404
    assert client.get(f"{API}/events").json()["items"] == []


def test_the_public_event_page_shows_tiers_and_remaining_tickets(
    client, db, make_event, make_tier, organiser
):
    event = make_event(organiser)
    tier = make_tier(event, name="Regular", quantity=10)
    tier.sold = 3
    tier.reserved = 2
    db.commit()

    response = client.get(f"{API}/events/{event.id}")

    assert response.status_code == 200
    tiers = response.json()["tiers"]
    assert [t["name"] for t in tiers] == ["Regular"]
    assert tiers[0]["remaining"] == 5


def test_browsing_lists_only_upcoming_published_events_soonest_first(
    client, make_event, organiser
):
    make_event(organiser, title="Later", starts_in=timedelta(days=10))
    make_event(organiser, title="Sooner", starts_in=timedelta(days=5))
    make_event(organiser, title="Draft", status=EventStatus.DRAFT, starts_in=timedelta(days=3))
    make_event(organiser, title="Past", starts_in=timedelta(days=-1))

    body = client.get(f"{API}/events").json()

    assert body["total"] == 2
    assert [item["title"] for item in body["items"]] == ["Sooner", "Later"]


def test_browsing_filters_by_city_category_and_date_range(client, make_event, organiser):
    make_event(organiser, title="Lagos Music", city="Lagos", category="music", starts_in=timedelta(days=5))
    make_event(organiser, title="Abuja Comedy", city="Abuja", category="comedy", starts_in=timedelta(days=10))
    make_event(organiser, title="Lagos Comedy", city="Lagos", category="comedy", starts_in=timedelta(days=20))

    def titles(**params):
        items = client.get(f"{API}/events", params=params).json()["items"]
        return {item["title"] for item in items}

    assert titles(city="lagos") == {"Lagos Music", "Lagos Comedy"}
    assert titles(category="COMEDY") == {"Abuja Comedy", "Lagos Comedy"}
    assert titles(city="Lagos", category="comedy") == {"Lagos Comedy"}
    assert titles(
        starts_after=iso(timedelta(days=7)), starts_before=iso(timedelta(days=15))
    ) == {"Abuja Comedy"}


def test_browsing_is_paginated(client, make_event, organiser):
    for number in range(3):
        make_event(organiser, title=f"Event {number}", starts_in=timedelta(days=number + 1))

    first = client.get(f"{API}/events", params={"size": 2}).json()
    second = client.get(f"{API}/events", params={"size": 2, "page": 2}).json()

    assert (first["total"], first["pages"], len(first["items"])) == (3, 2, 2)
    assert len(second["items"]) == 1


def test_browsing_rejects_a_reversed_date_range(client):
    response = client.get(
        f"{API}/events",
        params={
            "starts_after": iso(timedelta(days=10)),
            "starts_before": iso(timedelta(days=5)),
        },
    )

    assert response.status_code == 400