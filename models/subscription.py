import uuid
from sqlalchemy.dialects.postgresql import UUID
from .base import db
from sqlalchemy_serializer import SerializerMixin
from datetime import datetime

class Subscription(db.Model, SerializerMixin):
    __tablename__ = "subscriptions"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Paystack subscription IDs
    paystack_subscription_code = db.Column(db.String(255), nullable=False, unique=True, index=True)
    paystack_plan_code = db.Column(db.String(255), nullable=False)
    paystack_customer_code = db.Column(db.String(255), nullable=False, index=True)
    
    # Subscription details
    status = db.Column(db.Enum('active', 'cancelled', 'non-renewing', 'expired', name='subscription_status'), 
                      nullable=False, default='active')
    plan_type = db.Column(db.Enum('premium', 'premium_plus', name='subscription_plans'), nullable=False)
    
    # Paystack subscription specific
    email_token = db.Column(db.String(255), nullable=True)  # For Paystack auth
    subscription_interval = db.Column(db.String(20), nullable=False, default='monthly')  # monthly, yearly
    
    # Billing period (Paystack provides these)
    current_period_start = db.Column(db.DateTime, nullable=False)
    current_period_end = db.Column(db.DateTime, nullable=False)
    next_payment_date = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    __table_args__ = (
        db.Index('idx_subscriptions_status', 'status'),
        db.Index('idx_subscriptions_period_end', 'current_period_end'),
        db.Index('idx_subscriptions_next_payment', 'next_payment_date'),
    )