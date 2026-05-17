"""Add sectors and sector-based access control

Revision ID: 004
Revises: 003
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sectors table
    op.create_table(
        'sectors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_sectors_slug', 'sectors', ['slug'], unique=True)

    # Add sector_id to collections
    op.add_column(
        'collections',
        sa.Column('sector_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sectors.id', ondelete='SET NULL'), nullable=True)
    )
    op.create_index('idx_collections_sector', 'collections', ['sector_id'])

    # Add sector_id to integration_keys
    op.add_column(
        'integration_keys',
        sa.Column('sector_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sectors.id', ondelete='SET NULL'), nullable=True)
    )
    op.create_index('idx_integration_keys_sector', 'integration_keys', ['sector_id'])


def downgrade() -> None:
    op.drop_index('idx_integration_keys_sector')
    op.drop_column('integration_keys', 'sector_id')
    op.drop_index('idx_collections_sector')
    op.drop_column('collections', 'sector_id')
    op.drop_index('idx_sectors_slug')
    op.drop_table('sectors')
