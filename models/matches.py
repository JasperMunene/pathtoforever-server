import uuid
from sqlalchemy.dialects.postgresql import UUID
from .base import db
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import CheckConstraint

class Match(db.Model, SerializerMixin):
    __tablename__ = "matches" 
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id_1 = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user_id_2 = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    match_status = db.Column(db.Enum('pending', 'matched', 'declined', 'blocked', name='match_status'), nullable=False, default='pending')
    compatibility_score = db.Column(db.Integer, default=0)
    ai_explanation = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Ensure user_id_1 is always the smaller ID to prevent duplicate matches
    __table_args__ = (
        db.UniqueConstraint('user_id_1', 'user_id_2', name='uq_match_pair'),
        CheckConstraint('user_id_1 < user_id_2', name='check_user_order'),
    )