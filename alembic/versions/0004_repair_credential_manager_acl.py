"""Repair credential-manager access to platform integrations.

Revision ID: 0004_repair_credential_acl
Revises: 0003_repair_required
"""

from alembic import op


revision = "0004_repair_credential_acl"
down_revision = "0003_repair_required"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $repair$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'credential_manager')
               AND to_regclass('public.platform_integrations') IS NOT NULL THEN
                GRANT USAGE ON SCHEMA public TO credential_manager;
                GRANT SELECT, INSERT, UPDATE, DELETE
                    ON platform_integrations TO credential_manager;
                GRANT USAGE, SELECT
                    ON SEQUENCE platform_integrations_id_seq
                    TO credential_manager;

                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = 'platform_integrations'
                      AND policyname = 'credential_manager_access'
                ) THEN
                    CREATE POLICY credential_manager_access
                        ON platform_integrations
                        FOR ALL
                        TO credential_manager
                        USING (true)
                        WITH CHECK (true);
                END IF;
            END IF;
        END
        $repair$;
        """
    )


def downgrade() -> None:
    # Access may be shared with legacy SQL migrations, so removing it here could
    # break a database that was upgraded through those migrations.
    pass
