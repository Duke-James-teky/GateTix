
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.models.enums import UserRole
from app.models.event import Event
from app.models.growth import EventTeamMember
from app.models.user import User
from app.schemas.crew import CrewRole
from app.services.audit_service import log_event_action


def _get_event(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)

    if event is None:
        raise NotFoundError("Event not found")

    return event


def _require_event_owner(event: Event, actor: User) -> None:
    if event.organiser_id != actor.id:
        raise ForbiddenError(
            "Only the event organiser can manage the event team"
        )


def invite_member(
    db: Session,
    event_id: int,
    actor: User,
    user_id: int,
    role: CrewRole,
) -> EventTeamMember:
    event = _get_event(db, event_id)
    _require_event_owner(event, actor)

    if user_id == actor.id:
        raise ConflictError("You cannot invite yourself to your own event team")

    invitee = db.get(User, user_id)

    if invitee is None or not invitee.is_active:
        raise NotFoundError("User not found or inactive")

    if invitee.role != UserRole.ATTENDEE:
        raise ConflictError("Only attendees can be invited to an event team")

    existing = (
        db.query(EventTeamMember)
        .filter(
            EventTeamMember.event_id == event_id,
            EventTeamMember.user_id == user_id,
        )
        .first()
    )

    if existing is not None:
        if existing.status != "rejected":
            raise ConflictError(
                "This user already has an active or accepted team invitation"
            )

        existing.role = role
        existing.status = "pending"
        existing.invited_by = actor.id
        existing.accepted_at = None
        existing.responded_at = None
        member = existing
        action = "crew.invitation.resent"

    else:
        member = EventTeamMember(
            event_id=event_id,
            user_id=user_id,
            role=role,
            status="pending",
            invited_by=actor.id,
        )
        db.add(member)
        action = "crew.invitation.sent"

    log_event_action(
        db,
        event_id=event_id,
        actor_id=actor.id,
        action=action,
        details={
            "invited_user_id": user_id,
            "role": role,
        },
    )

    db.commit()
    db.refresh(member)

    return member


def respond_to_invitation(
    db: Session,
    invitation_id: int,
    actor: User,
    response: str,
) -> EventTeamMember:
    invitation = db.get(EventTeamMember, invitation_id)

    if invitation is None:
        raise NotFoundError("Team invitation not found")

    if invitation.user_id != actor.id:
        raise ForbiddenError(
            "You can only respond to your own team invitations"
        )

    if invitation.status != "pending":
        raise ConflictError("This invitation has already been responded to")

    if response not in ("accepted", "rejected"):
        raise ConflictError("Invalid invitation response")

    invitation.status = response

    if response == "accepted":
        invitation.accepted_at = __import__(
            "datetime"
        ).datetime.now(__import__("datetime").timezone.utc)

    from datetime import datetime, timezone

    invitation.responded_at = datetime.now(timezone.utc)

    log_event_action(
        db,
        event_id=invitation.event_id,
        actor_id=actor.id,
        action=f"crew.invitation.{response}",
        details={
            "team_member_id": invitation.id,
            "role": invitation.role,
        },
    )

    db.commit()
    db.refresh(invitation)

    return invitation


def list_team_members(
    db: Session,
    event_id: int,
    actor: User,
) -> list[EventTeamMember]:
    event = _get_event(db, event_id)
    _require_event_owner(event, actor)

    return (
        db.query(EventTeamMember)
        .filter(EventTeamMember.event_id == event_id)
        .order_by(EventTeamMember.created_at.desc())
        .all()
    )


def update_member_role(
    db: Session,
    event_id: int,
    member_id: int,
    actor: User,
    role: CrewRole,
) -> EventTeamMember:
    event = _get_event(db, event_id)
    _require_event_owner(event, actor)

    member = db.get(EventTeamMember, member_id)

    if member is None or member.event_id != event_id:
        raise NotFoundError("Team member not found")

    if member.status != "accepted":
        raise ConflictError(
            "You can only change the role of an accepted team member"
        )

    old_role = member.role
    member.role = role

    log_event_action(
        db,
        event_id=event_id,
        actor_id=actor.id,
        action="crew.member.role_updated",
        details={
            "team_member_id": member.id,
            "user_id": member.user_id,
            "old_role": old_role,
            "new_role": role,
        },
    )

    db.commit()
    db.refresh(member)

    return member


def remove_member(
    db: Session,
    event_id: int,
    member_id: int,
    actor: User,
) -> None:
    event = _get_event(db, event_id)
    _require_event_owner(event, actor)

    member = db.get(EventTeamMember, member_id)

    if member is None or member.event_id != event_id:
        raise NotFoundError("Team member not found")

    log_event_action(
        db,
        event_id=event_id,
        actor_id=actor.id,
        action="crew.member.removed",
        details={
            "team_member_id": member.id,
            "user_id": member.user_id,
            "role": member.role,
        },
    )

    db.delete(member)
    db.commit()
