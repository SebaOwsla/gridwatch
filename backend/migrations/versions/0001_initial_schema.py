"""Create the GridWatch relational schema and measurement hypertable.

Revision ID: 0001_initial_schema
Revises:
"""

from alembic import op


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The database image or administrator must provide the TimescaleDB extension.
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.execute("""
        CREATE TABLE users (
            id uuid PRIMARY KEY,
            email varchar(254) NOT NULL UNIQUE,
            password_hash varchar(255) NOT NULL,
            full_name varchar(120) NOT NULL,
            role varchar(16) NOT NULL,
            is_active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_users_email_lowercase CHECK (email = lower(email)),
            CONSTRAINT ck_users_role CHECK (role IN ('admin', 'operator', 'viewer'))
        )
    """)

    op.execute("""
        CREATE TABLE installations (
            id uuid PRIMARY KEY,
            code varchar(32) NOT NULL UNIQUE,
            name varchar(120) NOT NULL,
            kind varchar(20) NOT NULL,
            timezone varchar(64) NOT NULL DEFAULT 'America/Santiago',
            location varchar(160),
            is_active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_installations_kind
                CHECK (kind IN ('mine', 'hydroelectric', 'substation'))
        )
    """)

    op.execute("""
        CREATE TABLE equipment (
            id uuid PRIMARY KEY,
            installation_id uuid NOT NULL REFERENCES installations(id) ON DELETE RESTRICT,
            code varchar(32) NOT NULL,
            name varchar(120) NOT NULL,
            kind varchar(20) NOT NULL,
            status varchar(16) NOT NULL DEFAULT 'offline',
            nominal_voltage_v double precision,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_equipment_installation_code UNIQUE (installation_id, code),
            CONSTRAINT ck_equipment_kind
                CHECK (kind IN ('meter', 'transformer', 'generator', 'feeder', 'breaker')),
            CONSTRAINT ck_equipment_status
                CHECK (status IN ('online', 'offline', 'maintenance')),
            CONSTRAINT ck_equipment_nominal_voltage_positive
                CHECK (nominal_voltage_v IS NULL OR nominal_voltage_v > 0)
        )
    """)

    op.execute("""
        CREATE TABLE measurements (
            equipment_id uuid NOT NULL REFERENCES equipment(id) ON DELETE RESTRICT,
            measured_at timestamptz NOT NULL,
            received_at timestamptz NOT NULL DEFAULT now(),
            voltage_l1_v double precision,
            voltage_l2_v double precision,
            voltage_l3_v double precision,
            current_l1_a double precision,
            current_l2_a double precision,
            current_l3_a double precision,
            active_power_kw double precision,
            frequency_hz double precision,
            quality varchar(12) NOT NULL DEFAULT 'valid',
            source varchar(16) NOT NULL DEFAULT 'simulator',
            PRIMARY KEY (equipment_id, measured_at),
            CONSTRAINT ck_measurements_has_value CHECK (
                num_nonnulls(voltage_l1_v, voltage_l2_v, voltage_l3_v,
                    current_l1_a, current_l2_a, current_l3_a,
                    active_power_kw, frequency_hz) > 0
            ),
            CONSTRAINT ck_measurements_nonnegative_magnitudes CHECK (
                (voltage_l1_v IS NULL OR voltage_l1_v >= 0) AND
                (voltage_l2_v IS NULL OR voltage_l2_v >= 0) AND
                (voltage_l3_v IS NULL OR voltage_l3_v >= 0) AND
                (current_l1_a IS NULL OR current_l1_a >= 0) AND
                (current_l2_a IS NULL OR current_l2_a >= 0) AND
                (current_l3_a IS NULL OR current_l3_a >= 0) AND
                (frequency_hz IS NULL OR frequency_hz >= 0)
            ),
            CONSTRAINT ck_measurements_quality CHECK (quality IN ('valid', 'invalid')),
            CONSTRAINT ck_measurements_demo_only CHECK (source = 'simulator')
        )
    """)
    op.execute("SELECT create_hypertable('measurements', by_range('measured_at'))")

    op.execute("""
        CREATE TABLE alert_rules (
            id uuid PRIMARY KEY,
            equipment_id uuid NOT NULL REFERENCES equipment(id) ON DELETE RESTRICT,
            metric varchar(24) NOT NULL,
            min_value double precision,
            max_value double precision,
            is_enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_alert_rules_equipment_metric UNIQUE (equipment_id, metric),
            CONSTRAINT ck_alert_rules_metric CHECK (metric IN (
                'voltage_l1_v', 'voltage_l2_v', 'voltage_l3_v',
                'current_l1_a', 'current_l2_a', 'current_l3_a',
                'active_power_kw', 'frequency_hz'
            )),
            CONSTRAINT ck_alert_rules_has_bound
                CHECK (min_value IS NOT NULL OR max_value IS NOT NULL),
            CONSTRAINT ck_alert_rules_bounds_order
                CHECK (min_value IS NULL OR max_value IS NULL OR min_value < max_value)
        )
    """)

    op.execute("""
        CREATE TABLE alert_events (
            id uuid PRIMARY KEY,
            rule_id uuid NOT NULL REFERENCES alert_rules(id) ON DELETE RESTRICT,
            measurement_at timestamptz NOT NULL,
            observed_value double precision NOT NULL,
            status varchar(16) NOT NULL DEFAULT 'open',
            opened_at timestamptz NOT NULL DEFAULT now(),
            acknowledged_at timestamptz,
            acknowledged_by uuid REFERENCES users(id) ON DELETE RESTRICT,
            resolved_at timestamptz,
            CONSTRAINT ck_alert_events_status
                CHECK (status IN ('open', 'acknowledged', 'resolved'))
        )
    """)
    op.execute("""
        CREATE INDEX ix_alert_events_rule_status_opened
        ON alert_events (rule_id, status, opened_at)
    """)

    op.execute("""
        CREATE TABLE audit_events (
            id uuid PRIMARY KEY,
            actor_id uuid REFERENCES users(id) ON DELETE RESTRICT,
            action varchar(64) NOT NULL,
            entity_type varchar(64) NOT NULL,
            entity_id uuid,
            details jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_audit_events_created_at ON audit_events (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE audit_events")
    op.execute("DROP TABLE alert_events")
    op.execute("DROP TABLE alert_rules")
    op.execute("DROP TABLE measurements")
    op.execute("DROP TABLE equipment")
    op.execute("DROP TABLE installations")
    op.execute("DROP TABLE users")
    # Do not drop the shared TimescaleDB extension.
