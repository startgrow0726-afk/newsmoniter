"""Add short_interest table

Revision ID: 3ea496b872cb
Revises: a08328f3063f
Create Date: 2025-09-21 22:20:15.983453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ea496b872cb'
down_revision: Union[str, None] = 'a08328f3063f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('short_interest',
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('ticker', sa.Text(), nullable=False),
    sa.Column('short_volume', sa.BigInteger(), nullable=False),
    sa.Column('total_volume', sa.BigInteger(), nullable=False),
    sa.Column('short_volume_ratio', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('date', 'ticker')
    )
    op.create_index('ix_short_interest_ticker_date', 'short_interest', ['ticker', 'date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_short_interest_ticker_date', table_name='short_interest')
    op.drop_table('short_interest')