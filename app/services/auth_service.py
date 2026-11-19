from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

# A real hash of a throwaway password. When a login uses an unknown email, we still
# check against this, so the response takes the same time as a wrong password.
_DUMMY_HASH = hash_password("not-a-real-password")


def register_user(db: Session, data: RegisterRequest) -> User:
    """Create an attendee account. Raises ConflictError if the email is taken."""
    existing = db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise ConflictError("Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=UserRole.ATTENDEE,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two registrations with the same email raced; the database unique rule caught it.
        db.rollback()
        raise ConflictError("Email already registered") from None
    return user


def login_user(db: Session, data: LoginRequest) -> TokenResponse:
    """Check the email and password and return an access token."""
    user = db.scalar(select(User).where(User.email == data.email))

    if user is None:
        verify_password(data.password, _DUMMY_HASH)
        raise UnauthorizedError("Incorrect email or password")

    if not verify_password(data.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")

    if not user.is_active:
        raise ForbiddenError("This account has been deactivated")

    return TokenResponse(access_token=create_access_token(user.id))