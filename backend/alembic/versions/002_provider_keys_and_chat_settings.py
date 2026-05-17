"""Add provider_keys and chat_settings tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Provider Keys
    op.create_table(
        'provider_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('api_key_encrypted', sa.Text, nullable=False),
        sa.Column('api_key_hash', sa.String(64), nullable=False),
        sa.Column('label', sa.String(100)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('last_used_at', sa.DateTime),
        sa.Column('failure_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now())
    )
    op.create_index('idx_provider_keys_provider', 'provider_keys', ['provider'])
    op.create_index('idx_provider_keys_active', 'provider_keys', ['is_active'])

    # Chat Settings
    op.create_table(
        'chat_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('provider', sa.String(20), server_default='gemini'),
        sa.Column('model', sa.String(50), server_default='gemini-2.0-flash'),
        sa.Column('temperature', sa.Float, server_default='0.2'),
        sa.Column('top_p', sa.Float, server_default='0.6'),
        sa.Column('max_tokens', sa.Integer, server_default='2048'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now())
    )


def downgrade() -> None:
    op.drop_table('chat_settings')
    op.drop_index('idx_provider_keys_active')
    op.drop_index('idx_provider_keys_provider')
    op.drop_table('provider_keys')
