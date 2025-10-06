import logging
import os
import requests
import hmac
import hashlib
import json
from middleware.auth import clerk_required
from flask_restful import Resource
from flask import request
from models import db, User, Profile
from models.payments import Payment
from models.subscription import Subscription
from utils.response import success_response, error_response
from utils.emailer import send_email
from utils.email_templates import get_payment_success_email, get_renewal_reminder_email
from datetime import datetime, timedelta
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
        'name': 'Monthly Premium',
        'plan_code': 'PLN_v6fdrdvr3mowbzm'
    },
    'quarterly': {
        'amount': 260000,  # 2,600 KES (20% discount)
        'duration_days': 90,
        'name': 'Quarterly Premium',
        'plan_code': 'PLN_h3abepiqmirclin'
    },
    'yearly': {
        'amount': 1000000,  # 10,000 KES (33% discount)
        'duration_days': 365,
        'name': 'Yearly Premium',
        'plan_code': 'PLN_1pga9dyg1m5j2rq'

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
            
            # plan_type is the selected interval: monthly | quarterly | yearly
            plan_type = data.get('plan_type', 'monthly')
            # payment_method: 'card' (auto-renew) | 'mobile_money' (manual renew)
            payment_method = data.get('payment_method', 'card')
            
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
            # If a Paystack plan is supplied during initialization, Paystack will
            # automatically create a Subscription when the charge succeeds (card only).
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

            # Channel selection
            if payment_method == 'card':
                paystack_data['channels'] = ['card']
                # This is critical for subscriptions – pass the Paystack plan code for card payments only
                paystack_data['plan'] = plan['plan_code']
            elif payment_method == 'mobile_money':
                # Mpesa and other mobile money methods are one-off; no plan for subscriptions
                paystack_data['channels'] = ['mobile_money']
            
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

            # Extract Paystack customer/authorization if available
            customer_obj = transaction_data.get('customer') or {}
            authorization_obj = transaction_data.get('authorization') or {}
            paystack_customer_code = (
                customer_obj.get('customer_code')
                or customer_obj.get('code')
            )
            authorization_code = authorization_obj.get('authorization_code')
            if paystack_customer_code:
                payment.paystack_customer_code = paystack_customer_code

            subscription_created = None
            if payment.status == 'success':
                payment.paid_at = datetime.utcnow()

                # Determine selected plan and metadata
                meta = transaction_data.get('metadata') or {}
                selected_plan_code = transaction_data.get('plan') or SUBSCRIPTION_PLANS.get(meta.get('plan_type', 'monthly'), {}).get('plan_code')
                meta_plan_type = meta.get('plan_type', 'monthly')
                duration_days = SUBSCRIPTION_PLANS.get(meta_plan_type, {}).get('duration_days', 30)

                # Card flow: create/ensure subscription
                if payment.channel == 'card' and authorization_code and paystack_customer_code and selected_plan_code:
                    try:
                        sub_headers = {
                            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
                            'Content-Type': 'application/json'
                        }
                        sub_payload = {
                            'customer': paystack_customer_code,
                            'plan': selected_plan_code,
                            'authorization': authorization_code
                        }
                        sub_resp = requests.post(
                            f'{PAYSTACK_BASE_URL}/subscription',
                            json=sub_payload,
                            headers=sub_headers
                        )
                        if sub_resp.status_code == 200 and (sub_resp.json() or {}).get('status'):
                            sub_data = sub_resp.json().get('data', {})
                            subscription_code = sub_data.get('subscription_code') or sub_data.get('code')
                            email_token = sub_data.get('email_token')
                            sub_status = (sub_data.get('status') or 'active').lower()
                            next_payment_date_str = sub_data.get('next_payment_date')

                            # Compute current period bounds
                            now = datetime.utcnow()
                            current_period_start = now
                            current_period_end = None
                            if next_payment_date_str:
                                try:
                                    current_period_end = datetime.fromisoformat(next_payment_date_str.replace('Z', '+00:00'))
                                except Exception:
                                    pass
                            if not current_period_end:
                                current_period_end = now + timedelta(days=duration_days)

                            # Upsert subscription for this user
                            subscription = Subscription.query.filter_by(user_id=user_id).first()
                            if not subscription:
                                subscription = Subscription(
                                    user_id=user_id,
                                    paystack_subscription_code=subscription_code,
                                    paystack_plan_code=selected_plan_code,
                                    paystack_customer_code=paystack_customer_code,
                                    status=sub_status if sub_status in ['active', 'cancelled', 'non-renewing', 'expired'] else 'active',
                                    plan_type='premium',
                                    email_token=email_token,
                                    subscription_interval=meta_plan_type,
                                    current_period_start=current_period_start,
                                    current_period_end=current_period_end,
                                    next_payment_date=current_period_end
                                )
                                db.session.add(subscription)
                            else:
                                subscription.paystack_subscription_code = subscription_code or subscription.paystack_subscription_code
                                subscription.paystack_plan_code = selected_plan_code or subscription.paystack_plan_code
                                subscription.paystack_customer_code = paystack_customer_code or subscription.paystack_customer_code
                                subscription.email_token = email_token or subscription.email_token
                                subscription.status = sub_status if sub_status in ['active', 'cancelled', 'non-renewing', 'expired'] else subscription.status
                                subscription.subscription_interval = meta_plan_type
                                subscription.current_period_start = current_period_start
                                subscription.current_period_end = current_period_end
                                subscription.next_payment_date = current_period_end

                            subscription_created = True
                    except Exception as sub_e:
                        logger.error(f"Failed to create subscription on Paystack: {str(sub_e)}")

                # Non-card flow: grant access for the duration and set expiry
                else:
                    profile = Profile.query.filter_by(user_id=user_id).first()
                    if profile:
                        profile.premium = True
                        profile.premium_expires_at = datetime.utcnow() + timedelta(days=duration_days)
                        # Send email receipt and renewal info
                        try:
                            renew_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/discover"
                            subject = "🎉 Your Traliq Premium is Active!"
                            expires_formatted = profile.premium_expires_at.strftime('%B %d, %Y at %I:%M %p UTC')
                            html = get_payment_success_email(
                                plan_name=meta.get('plan_name', meta_plan_type.title()),
                                expires_at=expires_formatted,
                                renew_url=renew_url
                            )
                            send_email(user.email, subject, html)
                        except Exception as mail_e:
                            logger.warning(f"Failed to send confirmation email: {mail_e}")

                # Update user's premium status for card flow too
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
                    'premium_active': payment.status == 'success',
                    'subscription_created': bool(subscription_created)
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
        """Handle Paystack webhook events"""
        try:
            # Verify webhook signature using HMAC SHA512 with secret key
            signature = request.headers.get('x-paystack-signature')
            raw_body = request.get_data()  # raw bytes
            if not signature:
                return error_response("No signature provided", 400)

            computed = hmac.new(
                key=PAYSTACK_SECRET_KEY.encode('utf-8'),
                msg=raw_body,
                digestmod=hashlib.sha512
            ).hexdigest()
            if not hmac.compare_digest(computed, signature):
                logger.warning("Invalid Paystack webhook signature")
                return error_response("Invalid signature", 400)

            data = json.loads(raw_body.decode('utf-8')) if raw_body else {}
            event = data.get('event')

            if event == 'charge.success':
                transaction_data = data.get('data', {})
                reference = transaction_data.get('reference')

                payment = Payment.query.filter_by(paystack_reference=reference).first()
                if payment:
                    payment.status = 'success'
                    payment.paid_at = datetime.utcnow()
                    payment.paystack_transaction_id = str(transaction_data.get('id'))

                    # Set customer code if present
                    cust = (transaction_data.get('customer') or {})
                    paystack_customer_code = cust.get('customer_code') or cust.get('code')
                    if paystack_customer_code:
                        payment.paystack_customer_code = paystack_customer_code

                    # Activate premium; if non-card (e.g., mobile_money), set expiry
                    meta = transaction_data.get('metadata') or {}
                    plan_type = meta.get('plan_type', 'monthly')
                    duration_days = SUBSCRIPTION_PLANS.get(plan_type, {}).get('duration_days', 30)
                    profile = Profile.query.filter_by(user_id=payment.user_id).first()
                    if profile:
                        profile.premium = True
                        if transaction_data.get('channel') != 'card':
                            profile.premium_expires_at = datetime.utcnow() + timedelta(days=duration_days)
                            # Send email confirmation for manual payment
                            try:
                                user = User.query.get(payment.user_id)
                                renew_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/discover"
                                subject = "🎉 Your Traliq Premium is Active!"
                                expires_formatted = profile.premium_expires_at.strftime('%B %d, %Y at %I:%M %p UTC')
                                html = get_payment_success_email(
                                    plan_name=meta.get('plan_name', plan_type.title()),
                                    expires_at=expires_formatted,
                                    renew_url=renew_url
                                )
                                send_email(user.email, subject, html)
                            except Exception as mail_e:
                                logger.warning(f"Failed to send confirmation email: {mail_e}")

                    db.session.commit()
                    logger.info(f"Webhook: Payment {reference} marked as success")

            elif event in ('subscription.create', 'subscription.enable', 'subscription.disable', 'invoice.create'):
                payload = data.get('data', {})
                subscription_code = payload.get('subscription_code') or payload.get('code')
                customer = payload.get('customer') or {}
                paystack_customer_code = customer.get('customer_code') or customer.get('code')
                status = (payload.get('status') or '').lower()
                next_payment_date_str = payload.get('next_payment_date')

                # Find subscription by customer or code
                subscription = None
                if subscription_code:
                    subscription = Subscription.query.filter_by(paystack_subscription_code=subscription_code).first()
                if not subscription and paystack_customer_code:
                    subscription = Subscription.query.filter_by(paystack_customer_code=paystack_customer_code).first()

                if subscription:
                    if status in ['active', 'cancelled', 'non-renewing', 'expired'] and status:
                        subscription.status = status
                    if next_payment_date_str:
                        try:
                            next_dt = datetime.fromisoformat(next_payment_date_str.replace('Z', '+00:00'))
                            subscription.next_payment_date = next_dt
                            subscription.current_period_end = next_dt
                        except Exception:
                            pass
                    db.session.commit()

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
            
            # Fetch user's subscription if any
            subscription = Subscription.query.filter_by(user_id=user_id).first()

            # Get latest successful payment
            latest_payment = Payment.query.filter_by(
                user_id=user_id,
                status='success'
            ).order_by(Payment.paid_at.desc()).first()

            now = datetime.utcnow()
            has_valid_subscription = False
            sub_payload = None
            if subscription:
                has_valid_subscription = subscription.status in ['active', 'non-renewing'] and (
                    subscription.current_period_end is None or subscription.current_period_end >= now
                )
                sub_payload = {
                    'status': subscription.status,
                    'interval': subscription.subscription_interval,
                    'current_period_start': subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                    'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                    'next_payment_date': subscription.next_payment_date.isoformat() if subscription.next_payment_date else None,
                    'plan_code': subscription.paystack_plan_code,
                    'subscription_code': subscription.paystack_subscription_code
                }

            # Manual premium check via expiry
            premium_valid = False
            if profile.premium:
                if getattr(profile, 'premium_expires_at', None) is None:
                    premium_valid = True
                else:
                    premium_valid = profile.premium_expires_at >= now

            subscription_data = {
                'is_premium': premium_valid or has_valid_subscription,
                'has_access': premium_valid or has_valid_subscription,
                'subscription': sub_payload,
                'premium_expires_at': profile.premium_expires_at.isoformat() if getattr(profile, 'premium_expires_at', None) else None,
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
                    'savings': self._calculate_savings(plan_id),
                    'plan_code': plan_details.get('plan_code')
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


class RenewalReminderResource(Resource):
    """Send renewal reminders for manual (non-card) premium users."""

    def post(self):
        try:
            admin_key = request.headers.get('X-Admin-Key')
            expected = os.getenv('ADMIN_CRON_KEY')
            if not expected or admin_key != expected:
                return error_response("Unauthorized", 401)

            days_ahead = int(request.args.get('days_ahead', '3'))
            now = datetime.utcnow()
            upcoming = now + timedelta(days=days_ahead)

            # Find profiles that have manual expiry set and are premium
            profiles = Profile.query.filter(
                Profile.premium.is_(True),
                Profile.premium_expires_at.isnot(None),
                Profile.premium_expires_at <= upcoming
            ).all()

            count = 0
            for profile in profiles:
                user = User.query.get(profile.user_id)
                if not user or not user.email:
                    continue
                renew_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/subscribe"
                subject = "⏰ Your Traliq Premium is Expiring Soon"
                expires_formatted = profile.premium_expires_at.strftime('%B %d, %Y at %I:%M %p UTC')
                days_left = (profile.premium_expires_at - now).days
                html = get_renewal_reminder_email(
                    expires_at=expires_formatted,
                    renew_url=renew_url,
                    days_left=days_left
                )
                if send_email(user.email, subject, html):
                    count += 1

            return success_response({"reminders_sent": count}, "Renewal reminders processed")
        except Exception as e:
            logger.error(f"Renewal reminder error: {e}")
            return error_response("Failed to process reminders", 500)


class CancelSubscriptionResource(Resource):
    """Disable (cancel auto-renew) a user's subscription on Paystack"""

    @clerk_required
    def post(self):
        try:
            user_id = request.user.get('sub')
            subscription = Subscription.query.filter_by(user_id=user_id).first()
            if not subscription:
                return error_response("No active subscription found", 404)

            headers = {
                'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            payload = {
                'code': subscription.paystack_subscription_code,
                'token': subscription.email_token
            }
            resp = requests.post(f'{PAYSTACK_BASE_URL}/subscription/disable', json=payload, headers=headers)
            if resp.status_code != 200 or not (resp.json() or {}).get('status'):
                logger.error(f"Failed to disable subscription: {resp.text}")
                return error_response("Failed to cancel subscription", 500)

            subscription.status = 'non-renewing'
            db.session.commit()

            return success_response({'status': subscription.status}, "Subscription cancelled")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Cancel subscription error: {str(e)}")
            return error_response("Failed to cancel subscription", 500)


class EnableSubscriptionResource(Resource):
    """Enable a previously disabled subscription on Paystack"""

    @clerk_required
    def post(self):
        try:
            user_id = request.user.get('sub')
            subscription = Subscription.query.filter_by(user_id=user_id).first()
            if not subscription:
                return error_response("No subscription found", 404)

            headers = {
                'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            payload = {
                'code': subscription.paystack_subscription_code,
                'token': subscription.email_token
            }
            resp = requests.post(f'{PAYSTACK_BASE_URL}/subscription/enable', json=payload, headers=headers)
            if resp.status_code != 200 or not (resp.json() or {}).get('status'):
                logger.error(f"Failed to enable subscription: {resp.text}")
                return error_response("Failed to enable subscription", 500)

            subscription.status = 'active'
            db.session.commit()

            return success_response({'status': subscription.status}, "Subscription enabled")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Enable subscription error: {str(e)}")
            return error_response("Failed to enable subscription", 500)
