"""Make hub_forum_posts.hub_channel_id nullable.

`!forum create` typed in chat carries no channel selection of its own --
the target channel comes from the forums app bundle's own per-activation
`config.channel_id` (migration 069's 3-tier install -> tenant -> community
precedence, migration 091's `required_config`), which is empty (`{}`)
until an operator configures it via activation. A post must still persist
in that case (`core/svc_action/bundles/community_forums_action.py::
_resolve_channel_id` now returns `None` rather than rejecting the post),
so `hub_channel_id` can no longer be `NOT NULL`.

Revision ID: 0006_forum_nullable
Revises: 0005_repair_scoped_users
Create Date: 2026-09-04
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_forum_nullable"
down_revision = "0005_repair_scoped_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "hub_forum_posts",
        "hub_channel_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "hub_forum_posts",
        "hub_channel_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
