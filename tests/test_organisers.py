from app.models.enums import UserRole

API = "/api/v1"


def apply(client, headers, name="Lagos Live Events"):
    return client.post(
        f"{API}/organisers/apply", json={"organisation_name": name}, headers=headers
    )


def test_an_attendee_can_apply_to_become_an_organiser(client, auth, make_user):
    attendee = make_user()

    response = apply(client, auth(attendee))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["user_id"] == attendee.id
    assert body["organisation_name"] == "Lagos Live Events"
    assert body["reviewed_by"] is None


def test_a_second_pending_application_is_refused(client, auth, make_user):
    headers = auth(make_user())
    assert apply(client, headers).status_code == 201

    second = apply(client, headers)

    assert second.status_code == 409
    assert second.json()["detail"] == "You already have a pending application"


def test_a_rejected_applicant_can_apply_again(client, auth, make_user):
    admin = make_user(UserRole.ADMIN)
    headers = auth(make_user())
    application = apply(client, headers).json()
    rejected = client.patch(
        f"{API}/admin/organisers/{application['id']}",
        json={"status": "rejected"},
        headers=auth(admin),
    )
    assert rejected.status_code == 200

    assert apply(client, headers).status_code == 201


def test_only_attendees_can_apply(client, auth, make_user):
    assert apply(client, auth(make_user(UserRole.ORGANISER))).status_code == 403
    assert apply(client, auth(make_user(UserRole.ADMIN))).status_code == 403
    assert apply(client, {}).status_code == 401


def test_the_organisation_name_is_validated(client, auth, make_user):
    response = apply(client, auth(make_user()), name="A")

    assert response.status_code == 422