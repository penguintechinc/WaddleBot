"""Create `community_moderation_config` -- per-community content-moderation category toggles.

Per docs/plans/2026-09-08-content-moderation-design.md SS3/SS4: the P1
moderation gate (`core/svc_process/services/moderation_config.py`) reads
this table to resolve which classifier categories (`hate_speech`,
`basic_harassment`, `slurs`, ...) a community has opted into -- a proper
seam for the future admin UI (P3) rather than a hardcoded default. A
community with no row here (the common case -- every community starts
with moderation OFF) resolves to an empty `enabled_categories` set via the
gate's own `LEFT JOIN`, not a missing-row error.

Revision ID: 0008_moderation_config
Revises: 0007_forum_catalog
Create Date: 2026-09-08
"""

from alembic import op

revision = "0008_moderation_config"
down_revision = "0007_forum_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS community_moderation_config (
            community_id INTEGER PRIMARY KEY
                REFERENCES communities(id) ON DELETE CASCADE,
            enabled_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS community_moderation_config")
