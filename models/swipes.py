import uuid
from sqlalchemy.dialects.postgresql import UUID
from .base import db
from sqlalchemy_serializer import SerializerMixin

class Swipe(db.Model, SerializerMixin):
    __tablename__ = "swipes"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    swiper_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    swiped_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    direction = db.Column(db.Enum('like', 'dislike', 'super_like', name='swipe_direction'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Prevent duplicate swipes and ensure users can't swipe themselves
    __table_args__ = (
        db.UniqueConstraint('swiper_id', 'swiped_id', name='uq_swipe_pair'),
        db.CheckConstraint('swiper_id != swiped_id', name='check_no_self_swipe'),
        db.Index('idx_swiper_swiped', 'swiper_id', 'swiped_id'),
    )