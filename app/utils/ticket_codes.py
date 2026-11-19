import secrets


def generate_ticket_code() -> str:
    """Return a random, unguessable code for one ticket (about 22 characters)."""
    return secrets.token_urlsafe(16)