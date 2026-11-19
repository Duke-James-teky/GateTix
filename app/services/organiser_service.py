from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import ApplicationStatus, UserRole
from app.models.organiser_application import OrganiserApplication
from app.models.user import User
from app.schemas.admin import OrganiserDecision
from app.schemas.organiser import OrganiserApplicationCreate


def apply_to_become_organiser(
    db: Session, user: User, data: OrganiserApplicationCreate
) -> OrganiserApplication:
    """Create a pending application. A user may have only one pending at a time."""
    pending = db.scalar(
        select(OrganiserApplication).where(
            OrganiserApplication.user_id == user.id,
            OrganiserApplication.status == ApplicationStatus.PENDING,
        )
    )
    if pending is not None:
        raise ConflictError("You already have a pending application")

    application = OrganiserApplication(
        user_id=user.id,
        organisation_name=data.organisation_name,
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError:
        # Two applications raced; the database's one-pending-per-user rule caught it.
        db.rollback()
        raise ConflictError("You already have a pending application") from None
    return application


def review_application(
    db: Session, application_id: int, admin: User, decision: OrganiserDecision
) -> OrganiserApplication:
    """Approve or reject a pending application. Approval makes the applicant an organiser."""
    application = db.scalar(
        select(OrganiserApplication)
        .where(OrganiserApplication.id == application_id)
        .with_for_update()
    )
    if application is None:
        raise NotFoundError("Application not found")

    if application.status != ApplicationStatus.PENDING:
        raise ConflictError("This application has already been reviewed")

    application.status = ApplicationStatus(decision.status)
    application.reviewed_by = admin.id

    if application.status == ApplicationStatus.APPROVED:
        applicant = db.get(User, application.user_id)
        if applicant is not None:
            applicant.role = UserRole.ORGANISER

    db.commit()
    return application