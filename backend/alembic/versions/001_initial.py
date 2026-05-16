"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('pin_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), server_default='user'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Collections
    op.create_table(
        'collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('is_public', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Collection Access
    op.create_table(
        'collection_access',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('permission', sa.String(20), server_default='read'),
        sa.UniqueConstraint('collection_id', 'user_id')
    )
    
    # Documents
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE')),
        sa.Column('filename', sa.String(500)),
        sa.Column('file_type', sa.String(50)),
        sa.Column('file_size', sa.BigInteger),
        sa.Column('storage_path', sa.Text),
        sa.Column('status', sa.String(20), server_default='processing'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Chunks (pgvector)
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE')),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE')),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('embedding', sa.Text),  # Will be altered to VECTOR after table creation
        sa.Column('chunk_index', sa.Integer),
        sa.Column('hash', sa.String(64)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Alter embedding column to VECTOR
    op.execute('ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768) USING embedding::vector(768)')
    
    # Create indexes for chunks
    op.create_index('idx_chunks_embedding', 'chunks', ['embedding'], postgresql_using='ivfflat', 
                    postgresql_with={'lists': 100}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('idx_chunks_collection', 'chunks', ['collection_id'])
    op.create_index('idx_chunks_document', 'chunks', ['document_id'])
    
    # Entities
    op.create_table(
        'entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('type', sa.String(50)),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE')),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    op.create_index('idx_entities_type', 'entities', ['type'])
    op.create_index('idx_entities_collection', 'entities', ['collection_id'])
    
    # Relationships
    op.create_table(
        'relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE')),
        sa.Column('target_entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE')),
        sa.Column('relation_type', sa.String(100)),
        sa.Column('weight', sa.Float, server_default='1.0'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    op.create_index('idx_rel_source', 'relationships', ['source_entity_id'])
    op.create_index('idx_rel_target', 'relationships', ['target_entity_id'])
    op.create_index('idx_rel_type', 'relationships', ['relation_type'])
    
    # Integration Keys
    op.create_table(
        'integration_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(8), nullable=False),
        sa.Column('name', sa.String(100)),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('scoped_collections', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('last_used_at', sa.DateTime),
        sa.Column('expires_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Token Usage
    op.create_table(
        'token_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider', sa.String(20)),
        sa.Column('model', sa.String(50)),
        sa.Column('operation', sa.String(20)),
        sa.Column('tokens_in', sa.Integer),
        sa.Column('tokens_out', sa.Integer),
        sa.Column('cost_usd', sa.Float),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collections.id')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Execution Log
    op.create_table(
        'execution_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('operation', sa.String(50)),
        sa.Column('status', sa.String(20)),
        sa.Column('duration_ms', sa.Integer),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collections.id')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Error Log
    op.create_table(
        'error_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('level', sa.String(10)),
        sa.Column('source', sa.String(50)),
        sa.Column('message', sa.Text),
        sa.Column('traceback', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Server Metrics
    op.create_table(
        'server_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('disk_used_gb', sa.Float),
        sa.Column('disk_total_gb', sa.Float),
        sa.Column('ram_used_gb', sa.Float),
        sa.Column('ram_total_gb', sa.Float),
        sa.Column('cpu_percent', sa.Float),
        sa.Column('total_files', sa.Integer),
        sa.Column('total_chunks', sa.Integer),
        sa.Column('total_entities', sa.Integer),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Pricing
    op.create_table(
        'pricing',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider', sa.String(20)),
        sa.Column('model', sa.String(50)),
        sa.Column('input_price_per_1m', sa.Float),
        sa.Column('output_price_per_1m', sa.Float),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now())
    )


def downgrade() -> None:
    op.drop_table('pricing')
    op.drop_table('server_metrics')
    op.drop_table('error_log')
    op.drop_table('execution_log')
    op.drop_table('token_usage')
    op.drop_table('integration_keys')
    op.drop_table('relationships')
    op.drop_table('entities')
    op.drop_index('idx_chunks_embedding')
    op.drop_index('idx_chunks_collection')
    op.drop_index('idx_chunks_document')
    op.drop_table('chunks')
    op.drop_table('documents')
    op.drop_table('collection_access')
    op.drop_table('collections')
    op.drop_table('users')
