
from fastapi import APIRouter, status
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession, OrganiserUser
from app.schemas.crew import (
    CrewInviteCreate,
    CrewInvitationRespond,
    CrewMemberRead,
    CrewRoleUpdate,
)
from app.services import crew_service


router = APIRouter(prefix="/crew", tags=["GateTix Crew"])


@router.post(
    "/events/{event_id}/invitations",
    response_model=CrewMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a user to an event team",
)
def invite_team_member(
    event_id: int,
    data: CrewInviteCreate,
    organiser: OrganiserUser,
    db: DbSession,
):
    return crew_service.invite_member(
        db=db,
        event_id=event_id,
        actor=organiser,
        user_id=data.user_id,
        role=data.role,
    )


@router.post(
    "/invitations/{invitation_id}/respond",
    response_model=CrewMemberRead,
    summary="Accept or reject a team invitation",
)
def respond_to_team_invitation(
    invitation_id: int,
    data: CrewInvitationRespond,
    user: CurrentUser,
    db: DbSession,
):
    return crew_service.respond_to_invitation(
        db=db,
        invitation_id=invitation_id,
        actor=user,
        response=data.status,
    )


@router.get(
    "/events/{event_id}/members",
    response_model=list[CrewMemberRead],
    summary="List event team members",
)
def get_event_team(
    event_id: int,
    organiser: OrganiserUser,
    db: DbSession,
):
    return crew_service.list_team_members(
        db=db,
        event_id=event_id,
        actor=organiser,
    )


@router.patch(
    "/events/{event_id}/members/{member_id}/role",
    response_model=CrewMemberRead,
    summary="Update a team member's role",
)
def change_team_member_role(
    event_id: int,
    member_id: int,
    data: CrewRoleUpdate,
    organiser: OrganiserUser,
    db: DbSession,
):
    return crew_service.update_member_role(
        db=db,
        event_id=event_id,
        member_id=member_id,
        actor=organiser,
        role=data.role,
    )


@router.delete(
    "/events/{event_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a team member",
)
def remove_team_member(
    event_id: int,
    member_id: int,
    organiser: OrganiserUser,
    db: DbSession,
):
    crew_service.remove_member(
        db=db,
        event_id=event_id,
        member_id=member_id,
        actor=organiser,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
