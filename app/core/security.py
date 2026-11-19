from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from app.core.config import get_settings

settings = get_settings()

_password_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return _password_hasher.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(hash_password, plain_password)
    except (VerificationError, InvalidHashError):
        return False

def create_access_token(user_id: int) -> int:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "issued at": now,
        "expires": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["expires", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWKError, KeyError, ValueError):
        return None