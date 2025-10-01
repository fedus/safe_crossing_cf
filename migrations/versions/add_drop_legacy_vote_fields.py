"""Drop legacy crossing vote columns and meta table

Revision ID: drop_legacy_vote_fields
Revises: 37226d6e114d
Create Date: 2025-09-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'drop_legacy_vote_fields'
down_revision: Union[str, None] = '37226d6e114d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop columns from crossing if they exist
    with op.batch_alter_table('crossing') as batch_op:
        for col in ['votes_not_sure', 'votes_ok', 'votes_too_close', 'votes_total', 'current_result']:
            try:
                batch_op.drop_column(col)
            except Exception:
                pass

    # Drop meta table if exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'meta' in inspector.get_table_names():
        op.drop_table('meta')

    # Drop unique constraint on vote (user_id, crossing_id) if present
    # Constraint name may vary; attempt common name then fallback
    try:
        op.drop_constraint('vote_user_id_crossing_id_key', 'vote', type_='unique')
    except Exception:
        try:
            op.drop_constraint('uq_vote_user_crossing', 'vote', type_='unique')
        except Exception:
            # As last resort, recreate table constraints is avoided here
            pass


def downgrade() -> None:
    # Recreate meta table
    op.create_table(
        'meta',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('crossings_with_enough_votes', sa.Integer()),
        sa.Column('votes_not_sure', sa.Integer()),
        sa.Column('votes_ok', sa.Integer()),
        sa.Column('votes_too_close', sa.Integer()),
        sa.Column('votes_tie', sa.Integer()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # Add columns back to crossing
    with op.batch_alter_table('crossing') as batch_op:
        batch_op.add_column(sa.Column('votes_not_sure', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('votes_ok', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('votes_too_close', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('votes_total', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('current_result', sa.Integer(), nullable=True))

    # Re-add unique constraint on vote if desired
    try:
        op.create_unique_constraint('vote_user_id_crossing_id_key', 'vote', ['user_id', 'crossing_id'])
    except Exception:
        pass


