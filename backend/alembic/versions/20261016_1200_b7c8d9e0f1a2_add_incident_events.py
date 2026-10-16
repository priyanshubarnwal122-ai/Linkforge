"""Add persisted operational events and incidents."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("component", sa.String(length=80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_component", "incidents", ["component"])
    op.create_table(
        "operational_events",
        sa.Column("incident_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="info", nullable=False),
        sa.Column("component", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operational_events_incident_id", "operational_events", ["incident_id"])
    op.create_index("ix_operational_events_event_type", "operational_events", ["event_type"])
    op.create_index("ix_operational_events_component", "operational_events", ["component"])
    op.create_index("ix_operational_events_occurred_at", "operational_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_operational_events_occurred_at", table_name="operational_events")
    op.drop_index("ix_operational_events_component", table_name="operational_events")
    op.drop_index("ix_operational_events_event_type", table_name="operational_events")
    op.drop_index("ix_operational_events_incident_id", table_name="operational_events")
    op.drop_table("operational_events")
    op.drop_index("ix_incidents_component", table_name="incidents")
    op.drop_table("incidents")
