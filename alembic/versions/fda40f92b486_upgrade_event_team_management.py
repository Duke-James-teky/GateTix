
"""upgrade event team management

Revision ID: fda40f92b486
Revises: 4d475403ef5c
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fda40f92b486"
down_revision: Union[str, Sequence[str], None] = "4d475403ef5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add invitation status. Existing records initially receive pending.
    op.add_column(
        "event_team_members",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
    )

    op.add_column(
        "event_team_members",
        sa.Column(
            "responded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Preserve previously accepted memberships.
    op.execute(
        """
        UPDATE event_team_members
        SET status = 'accepted'
        WHERE accepted_at IS NOT NULL
        """
    )

    # Update the existing role constraint.
    op.drop_constraint(
        "ck_event_team_role",
        "event_team_members",
        type_="check",
    )

    op.create_check_constraint(
        "ck_event_team_role",
        "event_team_members",
        "role IN ('manager','checkin','finance','marketing','support')",
    )

    # Enforce valid invitation statuses.
    op.create_check_constraint(
        "ck_event_team_status",
        "event_team_members",
        "status IN ('pending','accepted','rejected')",
    )

    op.create_index(
        "ix_event_team_members_status",
        "event_team_members",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_team_members_status",
        table_name="event_team_members",
    )

    op.drop_constraint(
        "ck_event_team_status",
        "event_team_members",
        type_="check",
    )

    # Convert newer roles to an older supported role.
    op.execute(
        """
        UPDATE event_team_members
        SET role = 'checkin'
        WHERE role IN ('marketing', 'support')
        """
    )

    op.drop_constraint(
        "ck_event_team_role",
        "event_team_members",
        type_="check",
    )

    op.create_check_constraint(
        "ck_event_team_role",
        "event_team_members",
        "role IN ('manager','checkin','finance')",
    )

    op.drop_column("event_team_members", "responded_at")
    op.drop_column("event_team_members", "status")
