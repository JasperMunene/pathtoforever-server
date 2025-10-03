import uuid
from sqlalchemy.dialects.postgresql import UUID
from .base import db
from sqlalchemy_serializer import SerializerMixin

class Message(db.Model, SerializerMixin):
    __tablename__ = "messages"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = db.Column(UUID(as_uuid=True), db.ForeignKey('matches.id', ondelete='CASCADE'), nullable=False)
    sender_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    __table_args__ = (
        db.Index('idx_match_created', 'match_id', 'created_at'),
        db.Index('idx_sender_created', 'sender_id', 'created_at'),
    )