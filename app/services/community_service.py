
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.models.enums import UserRole
from app.models.event import Event
from app.models.growth import (
    CommunityAnnouncement,
    EventInvitation,
    EventSeries,
    OrganiserFollow,
)
from app.models.user import User
from app.schemas.community import (
    AnnouncementCreate,
    CommunityCreate,
    CommunityUpdate,
    InvitationCreate,
)


def create_community(
    db: Session, organiser: User, data: CommunityCreate
) -> EventSeries:
    community = EventSeries(
        organiser_id=organiser.id,
        title=data.title,
        description=data.description,
        is_public=data.is_public,
    )
    db.add(community)
    db.commit()
    db.refresh(community)
    return community


def list_public_communities(db: Session) -> list[EventSeries]:
    statement = (
        select(EventSeries)
        .where(EventSeries.is_public.is_(True))
        .order_by(EventSeries.created_at.desc())
    )
    return list(db.scalars(statement).all())


def list_my_communities(
    db: Session, organiser: User
) -> list[EventSeries]:
    statement = (
        select(EventSeries)
        .where(EventSeries.organiser_id == organiser.id)
        .order_by(EventSeries.created_at.desc())
    )
    return list(db.scalars(statement).all())


def get_community(db: Session, community_id: int) -> EventSeries:
    community = db.get(EventSeries, community_id)

    if community is None:
        raise NotFoundError("Community not found")

    return community


def update_community(
    db: Session,
    community_id: int,
    organiser: User,
    data: CommunityUpdate,
) -> EventSeries:
    community = get_community(db, community_id)

    if community.organiser_id != organiser.id:
        raise ForbiddenError(
            "You can only manage your own communities"
        )

    updates = data.model_dump(exclude_unset=True)

    if not updates:
        raise ConflictError(
            "Provide at least one field to update"
        )

    for field, value in updates.items():
        setattr(community, field, value)

    db.commit()
    db.refresh(community)

    return community


def follow_organiser(
    db: Session, attendee: User, organiser_id: int
) -> OrganiserFollow:
    if attendee.id == organiser_id:
        raise ConflictError("You cannot follow yourself")

    organiser = db.get(User, organiser_id)

    if organiser is None or not organiser.is_active:
        raise NotFoundError("Organiser not found")

    if organiser.role != UserRole.ORGANISER:
        raise ConflictError("This user is not an organiser")

    existing = db.scalar(
        select(OrganiserFollow).where(
            OrganiserFollow.follower_id == attendee.id,
            OrganiserFollow.organiser_id == organiser_id,
        )
    )

    if existing is not None:
        raise ConflictError("You already follow this organiser")

    follow = OrganiserFollow(
        follower_id=attendee.id,
        organiser_id=organiser_id,
    )
    db.add(follow)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "You already follow this organiser"
        ) from None

    db.refresh(follow)

    return follow


def unfollow_organiser(
    db: Session, attendee: User, organiser_id: int
) -> None:
    follow = db.scalar(
        select(OrganiserFollow).where(
            OrganiserFollow.follower_id == attendee.id,
            OrganiserFollow.organiser_id == organiser_id,
        )
    )

    if follow is None:
        raise NotFoundError(
            "You are not following this organiser"
        )

    db.delete(follow)
    db.commit()


def list_followed_organisers(
    db: Session, attendee: User
) -> list[OrganiserFollow]:
    statement = (
        select(OrganiserFollow)
        .where(OrganiserFollow.follower_id == attendee.id)
        .order_by(OrganiserFollow.created_at.desc())
    )

    return list(db.scalars(statement).all())


def publish_announcement(
    db: Session,
    organiser: User,
    data: AnnouncementCreate,
) -> CommunityAnnouncement:
    if data.series_id is not None:
        community = get_community(db, data.series_id)

        if community.organiser_id != organiser.id:
            raise ForbiddenError(
                "You can only publish in your own communities"
            )

    announcement = CommunityAnnouncement(
        organiser_id=organiser.id,
        series_id=data.series_id,
        title=data.title,
        body=data.body,
        published_at=datetime.now(timezone.utc),
    )

    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    return announcement


def list_community_announcements(
    db: Session, community_id: int
) -> list[CommunityAnnouncement]:
    community = get_community(db, community_id)

    if not community.is_public:
        raise NotFoundError("Community not found")

    statement = (
        select(CommunityAnnouncement)
        .where(
            CommunityAnnouncement.series_id == community_id
        )
        .where(
            CommunityAnnouncement.published_at.is_not(None)
        )
        .order_by(
            CommunityAnnouncement.published_at.desc()
        )
    )

    return list(db.scalars(statement).all())


def invite_to_event(
    db: Session,
    organiser: User,
    event_id: int,
    data: InvitationCreate,
) -> EventInvitation:
    event = db.get(Event, event_id)

    if event is None:
        raise NotFoundError("Event not found")

    if event.organiser_id != organiser.id:
        raise ForbiddenError(
            "You can only invite users to your own events"
        )

    invitee = db.get(User, data.invitee_id)

    if invitee is None or not invitee.is_active:
        raise NotFoundError("Attendee not found")

    if invitee.id == organiser.id:
        raise ConflictError("You cannot invite yourself")

    if invitee.role != UserRole.ATTENDEE:
        raise ConflictError(
            "Invitations can only be sent to attendees"
        )

    existing = db.scalar(
        select(EventInvitation).where(
            EventInvitation.event_id == event_id,
            EventInvitation.invitee_id == invitee.id,
        )
    )

    if existing is not None:
        raise ConflictError(
            "This user has already been invited"
        )

    invitation = EventInvitation(
        event_id=event_id,
        inviter_id=organiser.id,
        invitee_id=invitee.id,
    )

    db.add(invitation)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "This user has already been invited"
        ) from None

    db.refresh(invitation)

    return invitation


def list_my_invitations(
    db: Session, attendee: User
) -> list[EventInvitation]:
    statement = (
        select(EventInvitation)
        .where(EventInvitation.invitee_id == attendee.id)
        .order_by(EventInvitation.created_at.desc())
    )

    return list(db.scalars(statement).all())
