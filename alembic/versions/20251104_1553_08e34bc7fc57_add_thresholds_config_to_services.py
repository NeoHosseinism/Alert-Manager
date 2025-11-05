"""add_thresholds_config_to_services

Revision ID: 08e34bc7fc57
Revises: 20251103080000
Create Date: 2025-11-04 15:53:52.632268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08e34bc7fc57'
down_revision: Union[str, None] = '20251103080000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add thresholds_config JSON column to services table
    op.add_column('services', sa.Column('thresholds_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove thresholds_config column from services table
    op.drop_column('services', 'thresholds_config')
