"""rename customer_id db column to customerid

Revision ID: cda714162d42
Revises: 46293efaf42d
Create Date: 2026-05-31 03:18:46.082835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cda714162d42'
down_revision: Union[str, Sequence[str], None] = '46293efaf42d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Rename the column in place — preserves all data
    op.alter_column('payments', 'customer_id', new_column_name='customerid')
    # The index references the column by name, so we rename it too for consistency
    op.execute('ALTER INDEX ix_payments_customer_id RENAME TO ix_payments_customerid')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER INDEX ix_payments_customerid RENAME TO ix_payments_customer_id')
    op.alter_column('payments', 'customerid', new_column_name='customer_id')