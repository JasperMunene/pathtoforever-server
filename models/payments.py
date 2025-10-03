import uuid
from sqlalchemy.dialects.postgresql import UUID
from .base import db
from sqlalchemy_serializer import SerializerMixin

class Payment(db.Model, SerializerMixin):
    __tablename__ = "payments"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Paystack specific IDs
    paystack_reference = db.Column(db.String(255), nullable=False, unique=True, index=True)
    paystack_transaction_id = db.Column(db.String(255), nullable=True, index=True)
    paystack_customer_code = db.Column(db.String(255), nullable=True, index=True)
    
    # Payment details
    plan_type = db.Column(db.Enum('premium', 'boost', 'super_likes', name='plan_types'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # in cents (Paystack's currency unit)
    currency = db.Column(db.String(3), default='KES')  # Default to Kenyan Shilling
    
    # Paystack status mapping
    status = db.Column(db.Enum('pending', 'success', 'failed', 'abandoned', name='payment_status'), 
                      nullable=False, default='pending')
    
    # Additional Paystack fields
    authorization_url = db.Column(db.String(500), nullable=True)  # For redirects
    access_code = db.Column(db.String(100), nullable=True)
    channel = db.Column(db.String(50), nullable=True)  # card, bank_transfer, etc.
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    paid_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        db.Index('idx_payments_user_status', 'user_id', 'status'),
        db.Index('idx_payments_created', 'created_at'),
        db.Index('idx_payments_paystack_ref', 'paystack_reference'),
    )