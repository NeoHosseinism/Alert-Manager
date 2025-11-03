"""Add first_name and last_name to users table

Revision ID: 20251103072757
Revises: 2e833b5eada7
Create Date: 2025-11-03 07:27:57.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251103072757'
down_revision: Union[str, None] = '2e833b5eada7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add first_name and last_name columns to users table
    op.add_column('users', sa.Column('first_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove first_name and last_name columns from users table
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
