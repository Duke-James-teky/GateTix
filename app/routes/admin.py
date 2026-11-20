from fastapi import APIRouter, Depends

from app.core.dependencies import AdminUser, DbSession, require_admin
from app.routes.responses import CONFLICT, FORBIDDEN, NOT_FOUND, UNAUTHORIZED
from app.schemas.admin import EventModeration, OrganiserDecision, PlatformStats
from app.schemas.event import EventRead
from app.schemas.organiser import OrganiserApplicationRead
from app.services import admin_service, organiser_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.patch(
    "/organisers/{application_id}",
    response_model=OrganiserApplicationRead,
    summary="Approve or reject an organiser application",
    description=(
        "Admin only. `application_id` is the id of the **application**, not the user. "
        "Approving turns the applicant into an organiser straight away. "
        "A decision is final."
    ),
    responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def decide_organiser(
    application_id: int, decision: OrganiserDecision, admin: AdminUser, db: DbSession
):
    return organiser_service.review_application(db, application_id, admin, decision)


@router.patch(
    "/events/{event_id}",
    response_model=EventRead,
    summary="Suspend or restore an event",
    description=(
        "Admin only. `suspended` hides a published event and blocks new reservations. "
        "`published` restores a suspended event."
    ),
    dependencies=[Depends(require_admin)],
    responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT},
)
def moderate_event(event_id: int, decision: EventModeration, db: DbSession):
    return admin_service.moderate_event(db, event_id, decision)


@router.get(
    "/stats",
    response_model=PlatformStats,
    summary="Platform statistics",
    description=(
        "Admin only. Total events, tickets sold and revenue in kobo. "
        "Tickets and revenue count paid orders only, so refunds are excluded."
    ),
    dependencies=[Depends(require_admin)],
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def platform_stats(db: DbSession):
    return admin_service.get_platform_stats(db)