# models/user.py
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Index, func
from sqlalchemy_serializer import SerializerMixin
from .base import db


class User(db.Model, SerializerMixin):
    __tablename__ = "users"

    # Primary Key (Clerk user_id comes as a string UUID)
    id = Column(String, primary_key=True)

    # Basic Info
    name = Column(String(150), nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    avatar_url = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_users_email_lower", func.lower(email), unique=True),
        Index("ix_users_created_at", "created_at"),
    )
