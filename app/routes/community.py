from fastapi import APIRouter, status
from fastapi.responses import Response

from app.core.dependencies import (
    AttendeeUser,
    DbSession,
    OrganiserUser,
)
from app.routes.responses import CONFLICT, FORBIDDEN, UNAUTHORIZED
from app.schemas.community import (
    AnnouncementCreate,
    AnnouncementRead,
    CommunityCreate,
    CommunityRead,
    CommunityUpdate,
    FollowRead,
    InvitationCreate,
    InvitationRead,
)
from app.services import community_service


router = APIRouter(prefix="/community", tags=["Community"])


# --------------------------------------------------
# COMMUNITIES
# --------------------------------------------------

@router.post(
    "/communities",
    response_model=CommunityRead,
    status_code=status.HTTP_201_CREATED,
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def create_community(
    data: CommunityCreate,
    organiser: OrganiserUser,
    db: DbSession,
):
    return community_service.create_community(db, organiser, data)


@router.get(
    "/communities",
    response_model=list[CommunityRead],
)
def list_communities(db: DbSession):
    return community_service.list_public_communities(db)


@router.get(
    "/my/communities",
    response_model=list[CommunityRead],
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def list_my_communities(
    organiser: OrganiserUser,
    db: DbSession,
):
    return community_service.list_my_communities(db, organiser)


@router.patch(
    "/communities/{community_id}",
    response_model=CommunityRead,
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def update_community(
    community_id: int,
    data: CommunityUpdate,
    organiser: OrganiserUser,
    db: DbSession,
):
    return community_service.update_community(
        db, community_id, organiser, data
    )


# --------------------------------------------------
# COMMUNITY ANNOUNCEMENTS
# --------------------------------------------------

@router.post(
    "/announcements",
    response_model=AnnouncementRead,
    status_code=status.HTTP_201_CREATED,
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def publish_announcement(
    data: AnnouncementCreate,
    organiser: OrganiserUser,
    db: DbSession,
):
    return community_service.publish_announcement(
        db, organiser, data
    )


@router.get(
    "/communities/{community_id}/announcements",
    response_model=list[AnnouncementRead],
)
def list_community_announcements(
    community_id: int,
    db: DbSession,
):
    return community_service.list_community_announcements(
        db, community_id
    )


# --------------------------------------------------
# ORGANISER FOLLOWS
# --------------------------------------------------

@router.post(
    "/organisers/{organiser_id}/follow",
    response_model=FollowRead,
    status_code=status.HTTP_201_CREATED,
    responses={**UNAUTHORIZED, **FORBIDDEN, **CONFLICT},
)
def follow_organiser(
    organiser_id: int,
    attendee: AttendeeUser,
    db: DbSession,
):
    return community_service.follow_organiser(
        db, attendee, organiser_id
    )


@router.delete(
    "/organisers/{organiser_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def unfollow_organiser(
    organiser_id: int,
    attendee: AttendeeUser,
    db: DbSession,
):
    community_service.unfollow_organiser(
        db, attendee, organiser_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/my/following",
    response_model=list[FollowRead],
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def list_following(
    attendee: AttendeeUser,
    db: DbSession,
):
    return community_service.list_followed_organisers(
        db, attendee
    )


# --------------------------------------------------
# EVENT INVITATIONS
# --------------------------------------------------

@router.post(
    "/events/{event_id}/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
    responses={**UNAUTHORIZED, **FORBIDDEN, **CONFLICT},
)
def invite_to_event(
    event_id: int,
    data: InvitationCreate,
    organiser: OrganiserUser,
    db: DbSession,
):
    return community_service.invite_to_event(
        db, organiser, event_id, data
    )


@router.get(
    "/my/invitations",
    response_model=list[InvitationRead],
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def list_my_invitations(
    attendee: AttendeeUser,
    db: DbSession,
):
    return community_service.list_my_invitations(
        db, attendee
    )