import os
import logging
from flask import request
from flask_restful import Resource
from svix.webhooks import Webhook, WebhookVerificationError
from models import db, User, Profile

from utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class ClerkWebhook(Resource):
    """Handle Clerk webhook events"""

    def __init__(self):
        self.webhook_secret = os.getenv("CLERK_WEBHOOK_SECRET", "")

    def post(self):
        """Process Clerk webhook events"""
        try:
            if not self.webhook_secret:
                logger.error("CLERK_WEBHOOK_SECRET is missing")
                return error_response("Server misconfigured", 500)

            payload = request.data
            headers = dict(request.headers)

            # Verify webhook signature
            try:
                wh = Webhook(self.webhook_secret)
                data = wh.verify(payload, headers)
            except WebhookVerificationError:
                logger.warning("Webhook signature verification failed")
                return error_response("Invalid signature", 400)

            event_type = data.get("type")
            user_data = data.get("data", {})

            logger.info("Processing Clerk webhook event: %s", event_type)

            # Process different event types
            handler = getattr(self, f"_handle_{event_type.replace('.', '_')}", None)
            if handler:
                return handler(user_data)
            else:
                logger.info("Unhandled event type: %s", event_type)
                return success_response({"status": "ignored"}, "Event ignored")

        except Exception as e:
            db.session.rollback()
            logger.exception("Unhandled error in Clerk webhook")
            return error_response("Internal server error", 500)

    def _handle_user_created(self, user_data: dict):
        """Handle user.created event"""
        user_id = user_data.get("id")
        if not user_id:
            return error_response("Missing user ID", 400)

        # Check if user already exists
        if User.query.get(user_id):
            logger.info("User %s already exists", user_id)
            return success_response({"status": "exists"}, "User already exists")

        # Extract user data
        email = self._extract_email(user_data)
        name = self._extract_name(user_data)
        image_url = user_data.get("image_url") or user_data.get("profile_image_url")

        try:
            # Create user with correct field names from User model
            user = User(
                id=user_id,
                name=name,
                email=email or f"user_{user_id}@example.com",
                avatar_url=image_url,
            )
            db.session.add(user)
            # Flush to ensure user is in database before creating profile
            db.session.flush()

            # Create empty profile for the user
            profile = Profile(
                user_id=user.id,
            )
            db.session.add(profile)

            # Commit both user and profile
            db.session.commit()
            logger.info("Created user %s with profile", user_id)

            return success_response({"status": "created"}, "User and profile created successfully")

        except Exception as e:
            db.session.rollback()
            logger.error("Error creating user %s: %s", user_id, str(e))
            return error_response("Database error", 500)

    def _handle_user_updated(self, user_data: dict):
        """Handle user.updated event"""
        user_id = user_data.get("id")
        if not user_id:
            return error_response("Missing user ID", 400)

        user = User.query.get(user_id)
        if not user:
            logger.warning("User %s not found for update", user_id)
            return error_response("User not found", 404)

        try:
            # Update user fields with correct field names
            user.name = self._extract_name(user_data)
            user.email = self._extract_email(user_data) or user.email
            if user_data.get("image_url") or user_data.get("profile_image_url"):
                user.avatar_url = user_data.get("image_url") or user_data.get("profile_image_url")

            db.session.commit()
            logger.info("Updated user %s", user_id)

            return success_response({"status": "updated"}, "User updated successfully")

        except Exception as e:
            db.session.rollback()
            logger.error("Error updating user %s: %s", user_id, str(e))
            return error_response("Database error", 500)

    def _handle_user_deleted(self, user_data: dict):
        """Handle user.deleted event"""
        user_id = user_data.get("id")
        if not user_id:
            return error_response("Missing user ID", 400)

        user = User.query.get(user_id)
        if not user:
            logger.warning("User %s not found for deletion", user_id)
            return success_response({"status": "already_deleted"}, "User already deleted")

        try:
            # Profile will be cascade deleted due to ondelete='CASCADE'
            db.session.delete(user)
            db.session.commit()
            logger.info("Deleted user %s and associated profile", user_id)

            return success_response({"status": "deleted"}, "User deleted successfully")

        except Exception as e:
            db.session.rollback()
            logger.error("Error deleting user %s: %s", user_id, str(e))
            return error_response("Database error", 500)

    def _extract_email(self, user_data: dict) -> str:
        """Extract primary email from user data"""
        if user_data.get("email_addresses"):
            return user_data["email_addresses"][0].get("email_address")
        return ""

    def _extract_name(self, user_data: dict) -> str:
        """Extract full name from user data"""
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        name = (first_name + " " + last_name).strip()
        return name or user_data.get("username", "Unknown User")