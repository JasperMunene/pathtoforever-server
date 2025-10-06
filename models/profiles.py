import uuid
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, func, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy_serializer import SerializerMixin
from .base import db


class Profile(db.Model, SerializerMixin):
    __tablename__ = "profiles"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key to User
    user_id = Column(String, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Profile Information
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)
    height = Column(Integer, nullable=True)
    interests = Column(String(500), nullable=True)  # Comma-separated interests
    photos = Column(JSON, nullable=True)  # Array of photo URLs
    bio = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)

    # AI Embedding for matching (using pgvector)
    embedding = Column(Vector(768))

    # Premium Status
    premium = Column(Boolean, default=False)
    premium_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index("idx_profile_age_gender", "age", "gender"),
        Index("idx_profile_location", "location"),
        Index("idx_profile_user_id", "user_id"),
        Index("idx_profile_premium", "premium"),
        Index("idx_profile_premium_expires", "premium_expires_at"),
    )

    # Serialization rules
    serialize_rules = ('-embedding',)  # Exclude embedding from JSON serialization

    def __repr__(self):
        return f'<Profile {self.user_id}>'
