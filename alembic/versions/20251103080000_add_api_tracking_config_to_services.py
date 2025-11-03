"""Add api_tracking_config to services table

Revision ID: 20251103080000
Revises: 20251103072757
Create Date: 2025-11-03 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20251103080000'
down_revision: Union[str, None] = '20251103072757'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add api_tracking_config JSON column to services table
    # This allows flexible configuration of API tracking methods
    op.add_column(
        'services',
        sa.Column('api_tracking_config', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    # Remove api_tracking_config column from services table
    op.drop_column('services', 'api_tracking_config')
