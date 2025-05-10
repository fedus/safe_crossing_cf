"""add_fcm_token_to_user

Revision ID: 71d9f7fe3ec7
Revises: e06be225b414
Create Date: 2025-05-10 19:39:08.104683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '71d9f7fe3ec7'
down_revision = 'e06be225b414'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade schema."""
    op.add_column('user', sa.Column('fcm_token', sa.String(255), nullable=True))


def downgrade():
    """Downgrade schema."""
    op.drop_column('user', 'fcm_token')
