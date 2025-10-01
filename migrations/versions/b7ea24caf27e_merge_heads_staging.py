"""merge heads (staging)

Revision ID: b7ea24caf27e
Revises: drop_legacy_vote_fields, add_notification_log
Create Date: 2025-10-01 15:23:28.512585

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7ea24caf27e'
down_revision = ('drop_legacy_vote_fields', 'add_notification_log')
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade schema."""
    pass


def downgrade():
    """Downgrade schema."""
    pass
