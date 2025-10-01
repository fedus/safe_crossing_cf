"""add user_device_token table

Revision ID: add_user_device_token
Revises: b7ea24caf27e
Create Date: 2025-10-01
"""

from alembic import op
import sqlalchemy as sa


revision = 'add_user_device_token'
down_revision = 'b7ea24caf27e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'user_device_token' not in tables:
        op.create_table(
            'user_device_token',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('token', sa.String(length=255), nullable=False),
            sa.Column('platform', sa.String(length=20), nullable=True),
            sa.Column('valid', sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        )
        op.create_unique_constraint('uq_user_device_token_token', 'user_device_token', ['token'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'user_device_token' in tables:
        op.drop_constraint('uq_user_device_token_token', 'user_device_token', type_='unique')
        op.drop_table('user_device_token')


