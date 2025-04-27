"""Add information_text to City model

Revision ID: 5ebf212a4a56
Revises: 
Create Date: 2023-05-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '5ebf212a4a56'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add information_text column to city table if it doesn't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [column['name'] for column in inspector.get_columns('city')]
    
    if 'information_text' not in columns:
        op.add_column('city', sa.Column('information_text', sa.Text(), nullable=True))


def downgrade():
    # Remove information_text column from city table
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [column['name'] for column in inspector.get_columns('city')]
    
    if 'information_text' in columns:
        op.drop_column('city', 'information_text') 