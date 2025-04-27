"""Merge multiple heads

Revision ID: merge_heads_revision
Revises: fc470737f392, 5ebf212a4a56
Create Date: 2023-05-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads_revision'
down_revision = ('fc470737f392', '5ebf212a4a56')
branch_labels = None
depends_on = None


def upgrade():
    # No schema changes needed as this is just a merge migration
    pass


def downgrade():
    # No schema changes needed as this is just a merge migration
    pass 