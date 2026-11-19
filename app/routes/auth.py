from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new attendee account",
    description=(
        "Creates an account with the **attendee** role. "
        "Emails are stored in lowercase and must be unique."
    ),
    responses={409: {"model": ErrorResponse, "description": "Email already registered"}},
)
def register(data: RegisterRequest, db: DbSession):
    return auth_service.register_user(db, data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive an access token",
    description=(
        "Returns a JWT access token. In Swagger, copy the `access_token`, click "
        "**Authorize** at the top of the page, and paste it there."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Incorrect email or password"},
        403: {"model": ErrorResponse, "description": "Account deactivated"},
    },
)
def login(data: LoginRequest, db: DbSession):
    return auth_service.login_user(db, data)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Show the logged-in user",
    description="Returns the account that the access token belongs to. Handy for checking a token.",
    responses={401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"}},
)
def read_me(current_user: CurrentUser):
    return current_user