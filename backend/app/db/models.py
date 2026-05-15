"""SQLAlchemy ORM models for the RAG system."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB, VECTOR
from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    pin_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CollectionAccess(Base):
    __tablename__ = "collection_access"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    permission = Column(String(20), default="read")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"))
    filename = Column(String(500))
    file_type = Column(String(50))
    file_size = Column(BigInteger)
    storage_path = Column(Text)
    status = Column(String(20), default="processing")
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    embedding = Column(VECTOR(768))
    chunk_index = Column(Integer)
    hash = Column(String(64))
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    type = Column(String(50))
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"))
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class Relationship(Base):
    __tablename__ = "relationships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"))
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"))
    relation_type = Column(String(100))
    weight = Column(Float, default=1.0)
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class IntegrationKey(Base):
    __tablename__ = "integration_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(8), nullable=False)
    name = Column(String(100))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    scoped_collections = Column(ARRAY(UUID(as_uuid=True)), default=[])
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class TokenUsage(Base):
    __tablename__ = "token_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(20))
    model = Column(String(50))
    operation = Column(String(20))
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    cost_usd = Column(Float)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutionLog(Base):
    __tablename__ = "execution_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation = Column(String(50))
    status = Column(String(20))
    duration_ms = Column(Integer)
    metadata_ = Column("metadata", JSONB)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class ErrorLog(Base):
    __tablename__ = "error_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String(10))
    source = Column(String(50))
    message = Column(Text)
    traceback = Column(Text)
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class ServerMetrics(Base):
    __tablename__ = "server_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    disk_used_gb = Column(Float)
    disk_total_gb = Column(Float)
    ram_used_gb = Column(Float)
    ram_total_gb = Column(Float)
    cpu_percent = Column(Float)
    total_files = Column(Integer)
    total_chunks = Column(Integer)
    total_entities = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class Pricing(Base):
    __tablename__ = "pricing"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(20))
    model = Column(String(50))
    input_price_per_1m = Column(Float)
    output_price_per_1m = Column(Float)
    currency = Column(String(3), default="USD")
    updated_at = Column(DateTime, default=datetime.utcnow)
