
from app.models.enums import UserRole

API = "/api/v1/community"


def create_community(client, headers, title="Bonny Events"):
    return client.post(
        f"{API}/communities",
        json={
            "title": title,
            "description": "A community for event lovers.",
            "is_public": True,
        },
        headers=headers,
    )


def test_an_organiser_can_create_a_community(client, auth, make_user):
    organiser = make_user(UserRole.ORGANISER)

    response = create_community(client, auth(organiser))

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Bonny Events"
    assert body["organiser_id"] == organiser.id
    assert body["is_public"] is True


def test_only_organisers_can_create_communities(client, auth, make_user):
    attendee = make_user()
    admin = make_user(UserRole.ADMIN)

    assert create_community(client, auth(attendee)).status_code == 403
    assert create_community(client, auth(admin)).status_code == 403
    assert create_community(client, {}).status_code == 401


def test_public_communities_can_be_listed(client, auth, make_user):
    organiser = make_user(UserRole.ORGANISER)
    headers = auth(organiser)

    create_community(client, headers, "Public Community")

    response = client.get(f"{API}/communities")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Public Community"


def test_private_communities_are_not_listed_publicly(
    client, auth, make_user
):
    organiser = make_user(UserRole.ORGANISER)

    client.post(
        f"{API}/communities",
        json={
            "title": "Private Community",
            "description": "Private events",
            "is_public": False,
        },
        headers=auth(organiser),
    )

    response = client.get(f"{API}/communities")

    assert response.status_code == 200
    assert response.json() == []


def test_an_organiser_can_update_their_community(
    client, auth, make_user
):
    organiser = make_user(UserRole.ORGANISER)
    headers = auth(organiser)

    community = create_community(client, headers).json()

    response = client.patch(
        f"{API}/communities/{community['id']}",
        json={"title": "Updated Bonny Events"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Bonny Events"


def test_an_organiser_cannot_update_another_organisers_community(
    client, auth, make_user
):
    first_organiser = make_user(UserRole.ORGANISER)
    second_organiser = make_user(UserRole.ORGANISER)

    community = create_community(
        client, auth(first_organiser)
    ).json()

    response = client.patch(
        f"{API}/communities/{community['id']}",
        json={"title": "Unauthorised Update"},
        headers=auth(second_organiser),
    )

    assert response.status_code == 403


def test_an_attendee_can_follow_and_unfollow_an_organiser(
    client, auth, make_user
):
    attendee = make_user()
    organiser = make_user(UserRole.ORGANISER)

    headers = auth(attendee)

    follow = client.post(
        f"{API}/organisers/{organiser.id}/follow",
        headers=headers,
    )

    assert follow.status_code == 201
    assert follow.json()["follower_id"] == attendee.id
    assert follow.json()["organiser_id"] == organiser.id

    following = client.get(
        f"{API}/my/following",
        headers=headers,
    )

    assert following.status_code == 200
    assert len(following.json()) == 1

    unfollow = client.delete(
        f"{API}/organisers/{organiser.id}/follow",
        headers=headers,
    )

    assert unfollow.status_code == 204

    following_after = client.get(
        f"{API}/my/following",
        headers=headers,
    )

    assert following_after.json() == []


def test_an_attendee_cannot_follow_the_same_organiser_twice(
    client, auth, make_user
):
    attendee = make_user()
    organiser = make_user(UserRole.ORGANISER)

    headers = auth(attendee)
    url = f"{API}/organisers/{organiser.id}/follow"

    assert client.post(url, headers=headers).status_code == 201

    duplicate = client.post(url, headers=headers)

    assert duplicate.status_code == 409


def test_an_organiser_can_publish_a_community_announcement(
    client, auth, make_user
):
    organiser = make_user(UserRole.ORGANISER)
    headers = auth(organiser)

    community = create_community(client, headers).json()

    response = client.post(
        f"{API}/announcements",
        json={
            "title": "Upcoming Event",
            "body": "Join us for our next community event.",
            "series_id": community["id"],
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Upcoming Event"
    assert response.json()["organiser_id"] == organiser.id


def test_public_community_announcements_can_be_viewed(
    client, auth, make_user
):
    organiser = make_user(UserRole.ORGANISER)
    headers = auth(organiser)

    community = create_community(client, headers).json()

    client.post(
        f"{API}/announcements",
        json={
            "title": "Community Update",
            "body": "Here is an update for our members.",
            "series_id": community["id"],
        },
        headers=headers,
    )

    response = client.get(
        f"{API}/communities/{community['id']}/announcements"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Community Update"


def test_an_organiser_can_invite_an_attendee_to_an_event(
    client, auth, make_user, make_event
):
    organiser = make_user(UserRole.ORGANISER)
    attendee = make_user()

    event = make_event(organiser)

    response = client.post(
        f"{API}/events/{event.id}/invitations",
        json={"invitee_id": attendee.id},
        headers=auth(organiser),
    )

    assert response.status_code == 201
    assert response.json()["event_id"] == event.id
    assert response.json()["inviter_id"] == organiser.id
    assert response.json()["invitee_id"] == attendee.id

    invitations = client.get(
        f"{API}/my/invitations",
        headers=auth(attendee),
    )

    assert invitations.status_code == 200
    assert len(invitations.json()) == 1

def test_empty_community_update_is_rejected(client, auth, make_user):
    organiser = make_user(UserRole.ORGANISER)
    community = create_community(client, auth(organiser)).json()

    response = client.patch(
        f"{API}/communities/{community['id']}",
        json={},
        headers=auth(organiser),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Provide at least one field to update"


def test_event_invitation_is_rejected_for_non_attendee(
    client, auth, make_user, make_event
):
    organiser = make_user(UserRole.ORGANISER)
    another_organiser = make_user(UserRole.ORGANISER)
    event = make_event(organiser)

    response = client.post(
        f"{API}/events/{event.id}/invitations",
        json={"invitee_id": another_organiser.id},
        headers=auth(organiser),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Invitations can only be sent to attendees"