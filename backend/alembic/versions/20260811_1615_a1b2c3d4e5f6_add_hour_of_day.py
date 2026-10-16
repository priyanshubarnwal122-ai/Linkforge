"""Add hour_of_day to click_events for hourly heatmap.

Revision ID: a1b2c3d4e5f6
Revises: 5cc7840f849a
Create Date: 2026-08-11 16:15:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5cc7840f849a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add hour_of_day (0-23) column; NULL for historic rows, populated for all new clicks
    op.add_column(
        'click_events',
        sa.Column('hour_of_day', sa.Integer(), nullable=True)
    )
    # Back-fill existing rows from clicked_at so the heatmap works on old data too
    op.execute(
        "UPDATE click_events SET hour_of_day = EXTRACT(HOUR FROM clicked_at AT TIME ZONE 'UTC')"
    )


def downgrade() -> None:
    op.drop_column('click_events', 'hour_of_day')
