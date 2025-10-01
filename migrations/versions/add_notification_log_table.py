"""add notification_log table

Revision ID: add_notification_log
Revises: 71d9f7fe3ec7
Create Date: 2025-09-29
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_notification_log'
down_revision = '71d9f7fe3ec7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'notification_log' not in tables:
        op.create_table(
            'notification_log',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('created_by', sa.String(length=36), nullable=True),
            sa.Column('title', sa.String(length=200), nullable=True),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('data_json', sa.Text(), nullable=True),
            sa.Column('target_user_id', sa.String(length=36), nullable=True),
            sa.Column('sent_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('error_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('status', sa.String(length=32), nullable=True, server_default='logged'),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'notification_log' in tables:
        op.drop_table('notification_log')


