import pytest

API = "/api/v1"


def register(client, email="ada@example.com", password="Password123", name="Ada Obi"):
    return client.post(
        f"{API}/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def login(client, email="ada@example.com", password="Password123"):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def test_register_creates_an_attendee_and_hides_the_password(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["role"] == "attendee"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_rejects_a_duplicate_email_in_any_letter_case(client):
    assert register(client).status_code == 201

    response = register(client, email="ADA@Example.com")

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Ada Obi", "email": "ada@example.com", "password": "short1"},
        {"name": "Ada Obi", "email": "not-an-email", "password": "Password123"},
        {"name": "A", "email": "ada@example.com", "password": "Password123"},
    ],
)
def test_register_rejects_invalid_input(client, payload):
    response = client.post(f"{API}/auth/register", json=payload)

    assert response.status_code == 422


def test_login_returns_a_token_that_works(client):
    register(client)

    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    me = client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


def test_login_gives_the_same_error_for_a_wrong_password_and_an_unknown_email(client):
    register(client)

    wrong_password = login(client, password="WrongPassword1")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_protected_endpoint_rejects_missing_and_invalid_tokens(client):
    assert client.get(f"{API}/auth/me").status_code == 401

    bad = client.get(f"{API}/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


def test_deactivated_account_cannot_log_in_or_use_an_old_token(client, db, make_user, auth):
    user = make_user(email="gone@example.com", password="Password123")
    headers = auth(user)
    user.is_active = False
    db.commit()

    assert login(client, email="gone@example.com").status_code == 403
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401