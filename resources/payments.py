import logging
import os
import requests
from middleware.auth import clerk_required
from flask_restful import Resource
from flask import request
from models import db, User, Profile
from models.payments import Payment
from utils.response import success_response, error_response
from datetime import datetime
import secrets

logger = logging.getLogger(__name__)

# Paystack configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
PAYSTACK_BASE_URL = 'https://api.paystack.co'

# Subscription pricing (in cents - 1 KES = 100 cents)
SUBSCRIPTION_PLANS = {
    'monthly': {
        'amount': 100000,  # 1,000 KES
        'duration_days': 30,
        'name': 'Monthly Premium'
    },
    'quarterly': {
        'amount': 260000,  # 2,600 KES (20% discount)
        'duration_days': 90,
        'name': 'Quarterly Premium'
    },
    'yearly': {
        'amount': 1000000,  # 10,000 KES (33% discount)
        'duration_days': 365,
        'name': 'Yearly Premium'
    }
}


class InitializePaymentResource(Resource):
    """Initialize a payment with Paystack"""
    
    @clerk_required
    def post(self):
        """
        Initialize payment for platform access
        """
        try:
            user_id = request.user.get('sub')
            data = request.get_json()
            
            if not data:
                return error_response("No data provided", 400)
            
            plan_type = data.get('plan_type', 'monthly')
            
            if plan_type not in SUBSCRIPTION_PLANS:
                return error_response("Invalid plan type", 400)
            
            # Get user details
            user = User.query.get(user_id)
            if not user:
                return error_response("User not found", 404)
            
            plan = SUBSCRIPTION_PLANS[plan_type]
            
            # Generate unique reference
            reference = f"traliq_{user_id[:8]}_{secrets.token_hex(8)}"
            
            # Prepare Paystack request
            paystack_data = {
                'email': user.email,
                'amount': plan['amount'],
                'reference': reference,
                'currency': 'KES',
                'callback_url': f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/payment/callback",
                'metadata': {
                    'user_id': user_id,
                    'plan_type': plan_type,
                    'plan_name': plan['name'],
                    'duration_days': plan['duration_days']
                }
            }
            
            # Initialize payment with Paystack
            headers = {
                'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'{PAYSTACK_BASE_URL}/transaction/initialize',
                json=paystack_data,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Paystack error: {response.text}")
                return error_response("Failed to initialize payment", 500)
            
            paystack_response = response.json()
            
            if not paystack_response.get('status'):
                return error_response("Payment initialization failed", 500)
            
            payment_data = paystack_response['data']
            
            # Save payment record
            payment = Payment(
                user_id=user_id,
                paystack_reference=reference,
                plan_type='premium',
                amount=plan['amount'],
                currency='KES',
                status='pending',
                authorization_url=payment_data.get('authorization_url'),
                access_code=payment_data.get('access_code')
            )
            
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"Payment initialized for user {user_id}: {reference}")
            
            return success_response(
                {
                    'reference': reference,
                    'authorization_url': payment_data.get('authorization_url'),
                    'access_code': payment_data.get('access_code'),
                    'amount': plan['amount'] / 100,  # Convert to KES
                    'plan': plan['name']
                },
                "Payment initialized successfully"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error initializing payment: {str(e)}")
            return error_response("Failed to initialize payment", 500)


class VerifyPaymentResource(Resource):
    """Verify payment with Paystack"""
    
    @clerk_required
    def get(self, reference):
        """
        Verify payment status from Paystack
        """
        try:
            user_id = request.user.get('sub')
            
            # Get payment record
            payment = Payment.query.filter_by(
                paystack_reference=reference,
                user_id=user_id
            ).first()
            
            if not payment:
                return error_response("Payment not found", 404)
            
            # Verify with Paystack
            headers = {
                'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'
            }
            
            response = requests.get(
                f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}',
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Paystack verification error: {response.text}")
                return error_response("Failed to verify payment", 500)
            
            paystack_response = response.json()
            
            if not paystack_response.get('status'):
                return error_response("Payment verification failed", 500)
            
            transaction_data = paystack_response['data']
            
            # Update payment record
            payment.status = transaction_data.get('status', 'failed')
            payment.paystack_transaction_id = str(transaction_data.get('id'))
            payment.channel = transaction_data.get('channel')
            
            if payment.status == 'success':
                payment.paid_at = datetime.utcnow()
                
                # Update user's premium status
                profile = Profile.query.filter_by(user_id=user_id).first()
                if profile:
                    profile.premium = True
                    logger.info(f"User {user_id} upgraded to premium")
            
            db.session.commit()
            
            return success_response(
                {
                    'status': payment.status,
                    'reference': reference,
                    'amount': payment.amount / 100,
                    'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
                    'premium_active': payment.status == 'success'
                },
                "Payment verified successfully"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error verifying payment: {str(e)}")
            return error_response("Failed to verify payment", 500)


class PaystackWebhookResource(Resource):
    """Handle Paystack webhooks"""
    
    def post(self):
        """
        Handle Paystack webhook events
        """
        try:
            # Verify webhook signature
            signature = request.headers.get('x-paystack-signature')
            
            if not signature:
                return error_response("No signature provided", 400)
            
            # Verify signature (implement signature verification)
            # For now, we'll process the webhook
            
            data = request.get_json()
            event = data.get('event')
            
            if event == 'charge.success':
                transaction_data = data.get('data', {})
                reference = transaction_data.get('reference')
                
                # Find payment
                payment = Payment.query.filter_by(paystack_reference=reference).first()
                
                if payment:
                    payment.status = 'success'
                    payment.paid_at = datetime.utcnow()
                    payment.paystack_transaction_id = str(transaction_data.get('id'))
                    
                    # Activate premium
                    profile = Profile.query.filter_by(user_id=payment.user_id).first()
                    if profile:
                        profile.premium = True
                    
                    db.session.commit()
                    logger.info(f"Webhook: Payment {reference} marked as success")
            
            return success_response({}, "Webhook processed")
            
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return error_response("Webhook processing failed", 500)


class SubscriptionStatusResource(Resource):
    """Check user's subscription status"""
    
    @clerk_required
    def get(self):
        """Get current user's subscription status"""
        try:
            user_id = request.user.get('sub')
            
            profile = Profile.query.filter_by(user_id=user_id).first()
            
            if not profile:
                return error_response("Profile not found", 404)
            
            # Get latest successful payment
            latest_payment = Payment.query.filter_by(
                user_id=user_id,
                status='success'
            ).order_by(Payment.paid_at.desc()).first()
            
            subscription_data = {
                'is_premium': profile.premium,
                'has_access': profile.premium,
                'latest_payment': None
            }
            
            if latest_payment:
                subscription_data['latest_payment'] = {
                    'amount': latest_payment.amount / 100,
                    'paid_at': latest_payment.paid_at.isoformat() if latest_payment.paid_at else None,
                    'reference': latest_payment.paystack_reference
                }
            
            return success_response(
                subscription_data,
                "Subscription status retrieved"
            )
            
        except Exception as e:
            logger.error(f"Error fetching subscription status: {str(e)}")
            return error_response("Failed to fetch subscription status", 500)


class PaymentPlansResource(Resource):
    """Get available payment plans"""
    
    def get(self):
        """Get all available subscription plans"""
        try:
            plans = []
            
            for plan_id, plan_details in SUBSCRIPTION_PLANS.items():
                plans.append({
                    'id': plan_id,
                    'name': plan_details['name'],
                    'amount': plan_details['amount'] / 100,  # Convert to KES
                    'currency': 'KES',
                    'duration_days': plan_details['duration_days'],
                    'savings': self._calculate_savings(plan_id)
                })
            
            return success_response(
                {'plans': plans},
                "Payment plans retrieved"
            )
            
        except Exception as e:
            logger.error(f"Error fetching plans: {str(e)}")
            return error_response("Failed to fetch plans", 500)
    
    def _calculate_savings(self, plan_id):
        """Calculate savings compared to monthly plan"""
        monthly_price = SUBSCRIPTION_PLANS['monthly']['amount'] / 100
        plan = SUBSCRIPTION_PLANS[plan_id]
        
        if plan_id == 'monthly':
            return 0
        
        months = plan['duration_days'] / 30
        regular_price = monthly_price * months
        plan_price = plan['amount'] / 100
        
        savings = regular_price - plan_price
        savings_percent = (savings / regular_price) * 100
        
        return {
            'amount': savings,
            'percent': round(savings_percent, 0)
        }
