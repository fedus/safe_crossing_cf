"""Add icon_url and subtitle to City model

Revision ID: e06be225b414
Revises: fc470737f392
Create Date: 2025-04-27 20:57:50.566234

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'e06be225b414'
down_revision = 'fc470737f392'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade schema."""
    # Add icon_url and subtitle columns to city table if they don't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [column['name'] for column in inspector.get_columns('city')]
    
    if 'icon_url' not in columns:
        op.add_column('city', sa.Column('icon_url', sa.String(255), nullable=True))
    
    if 'subtitle' not in columns:
        op.add_column('city', sa.Column('subtitle', sa.String(255), nullable=True))


def downgrade():
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [column['name'] for column in inspector.get_columns('city')]
    
    if 'subtitle' in columns:
        op.drop_column('city', 'subtitle')
        
    if 'icon_url' in columns:
        op.drop_column('city', 'icon_url')
