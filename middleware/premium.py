import logging
from functools import wraps
from flask import request
from models import Profile
from utils.response import error_response

logger = logging.getLogger(__name__)


def premium_required(f):
    """
    Decorator to require premium subscription for accessing routes
    Must be used after @clerk_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get user_id from request (set by clerk_required)
            user_id = request.user.get('sub')
            
            if not user_id:
                return error_response("Authentication required", 401)
            
            # Check if user has premium access
            profile = Profile.query.filter_by(user_id=user_id).first()
            
            if not profile:
                return error_response("Profile not found", 404)
            
            if not profile.premium:
                return error_response(
                    "Premium subscription required to access this feature",
                    403,
                    {
                        'requires_premium': True,
                        'message': 'Please subscribe to access the platform'
                    }
                )
            
            # User has premium access, proceed
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Premium check error: {str(e)}")
            return error_response("Failed to verify premium status", 500)
    
    return decorated_function
