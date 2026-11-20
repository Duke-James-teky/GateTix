from fastapi import APIRouter, status

from app.core.dependencies import AttendeeUser, DbSession
from app.routes.responses import CONFLICT, FORBIDDEN, UNAUTHORIZED
from app.schemas.organiser import OrganiserApplicationCreate, OrganiserApplicationRead
from app.services import organiser_service

router = APIRouter(prefix="/organisers", tags=["Organisers"])


@router.post(
    "/apply",
    response_model=OrganiserApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to become an organiser",
    description=(
        "Only attendees can apply. You may have one pending application at a time. "
        "An admin approves or rejects it."
    ),
    responses={**UNAUTHORIZED, **FORBIDDEN, **CONFLICT},
)
def apply(data: OrganiserApplicationCreate, user: AttendeeUser, db: DbSession):
    return organiser_service.apply_to_become_organiser(db, user, data)