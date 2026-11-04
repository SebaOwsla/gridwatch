"""Allow at most one active alert event for each rule.

Revision ID: 0002_one_active_alert_per_rule
Revises: 0001_initial_schema
"""

from alembic import op


revision = "0002_one_active_alert_per_rule"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE UNIQUE INDEX uq_alert_events_one_active_per_rule
        ON alert_events (rule_id)
        WHERE status IN ('open', 'acknowledged')
    """)


def downgrade() -> None:
    op.execute("DROP INDEX uq_alert_events_one_active_per_rule")
