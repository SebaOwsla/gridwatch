"""Create OSS-compatible maintenance function for simulated measurements.

Revision ID: 0003_measurement_retention
Revises: 0002_one_active_alert_per_rule
"""

from alembic import op


revision = "0003_measurement_retention"
down_revision = "0002_one_active_alert_per_rule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The Apache edition supports drop_chunks, but not add_retention_policy.
    # Compose calls this once a day through its retention service.
    op.execute("""
        CREATE FUNCTION public.gridwatch_apply_measurement_retention()
        RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM drop_chunks('measurements', older_than => INTERVAL '35 days');
        END
        $$
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION public.gridwatch_apply_measurement_retention()")
