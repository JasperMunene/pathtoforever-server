import logging
from middleware.auth import clerk_required
from flask_restful import Resource, reqparse
from flask import request
from models import db, User, Profile
from utils.response import success_response, error_response
from utils.embeddings import generate_profile_embedding
from utils.cache import CacheManager

logger = logging.getLogger(__name__)


class CurrentUserResource(Resource):
    """Resource for current authenticated user's profile"""
    
    @clerk_required
    def get(self):
        """Get current user's profile"""
        try:
            user_id = request.user.get('sub')
            
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return error_response("User not found", 404)
            
            profile = Profile.query.filter_by(user_id=user_id).first()
            if not profile:
                logger.warning(f"Profile for user {user_id} not found")
                return error_response("Profile not found", 404)
            
            # Serialize user and profile data
            user_data = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'avatar_url': user.avatar_url,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'profile': {
                    'id': str(profile.id),
                    'age': profile.age,
                    'gender': profile.gender,
                    'height': profile.height,
                    'interests': profile.interests,
                    'photos': profile.photos,
                    'bio': profile.bio,
                    'location': profile.location,
                    'premium': profile.premium,
                    'created_at': profile.created_at.isoformat() if profile.created_at else None,
                    'updated_at': profile.updated_at.isoformat() if profile.updated_at else None,
                }
            }
            
            return success_response(user_data, "User profile retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return error_response("Failed to fetch profile", 500)
    
    @clerk_required
    def put(self):
        """Update current user's profile (full update)"""
        try:
            user_id = request.user.get('sub')
            data = request.get_json()
            
            if not data:
                return error_response("No data provided", 400)
            
            # Get user and profile
            user = User.query.get(user_id)
            if not user:
                return error_response("User not found", 404)
            
            profile = Profile.query.filter_by(user_id=user_id).first()
            if not profile:
                return error_response("Profile not found", 404)
            
            # Update user fields if provided
            if 'name' in data:
                user.name = data['name']
            if 'email' in data:
                # Check if email is unique
                existing = User.query.filter(User.email == data['email'], User.id != user_id).first()
                if existing:
                    return error_response("Email already in use", 400)
                user.email = data['email']
            
            # Update profile fields
            if 'age' in data:
                profile.age = data['age']
            if 'gender' in data:
                profile.gender = data['gender']
            if 'height' in data:
                profile.height = data['height']
            if 'interests' in data:
                profile.interests = data['interests']
            if 'photos' in data:
                profile.photos = data['photos']
            if 'bio' in data:
                profile.bio = data['bio']
            if 'location' in data:
                profile.location = data['location']
            
            # Generate embedding if bio or interests are updated
            if 'bio' in data or 'interests' in data:
                logger.info(f"Generating embedding for user {user_id}")
                embedding = generate_profile_embedding(
                    bio=profile.bio or '',
                    interests=profile.interests or ''
                )
                
                if embedding:
                    profile.embedding = embedding
                    logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
                else:
                    logger.warning(f"Failed to generate embedding for user {user_id}")
            
            db.session.commit()
            logger.info(f"Updated profile for user {user_id}")
            
            # Invalidate user cache to refresh matches
            CacheManager.invalidate_user_cache(user_id)
            logger.info(f"Invalidated cache for user {user_id} after profile update")
            
            return success_response(
                {'user_id': user_id, 'updated': True},
                "Profile updated successfully"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating profile: {str(e)}")
            return error_response("Failed to update profile", 500)
    
    @clerk_required
    def patch(self):
        """Partially update current user's profile"""
        # PATCH uses the same logic as PUT for partial updates
        return self.put()


class UserProfileResource(Resource):
    """Resource for viewing other users' profiles (for matches)"""
    
    @clerk_required
    def get(self, user_id):
        """Get another user's public profile"""
        try:
            current_user_id = request.user.get('sub')
            
            # Check if requesting own profile
            if user_id == current_user_id:
                return error_response("Use /users/me for your own profile", 400)
            
            user = User.query.get(user_id)
            if not user:
                return error_response("User not found", 404)
            
            profile = Profile.query.filter_by(user_id=user_id).first()
            if not profile:
                return error_response("Profile not found", 404)
            
            # Return public profile data only (no email)
            public_data = {
                'id': user.id,
                'name': user.name,
                'avatar_url': user.avatar_url,
                'profile': {
                    'age': profile.age,
                    'gender': profile.gender,
                    'height': profile.height,
                    'interests': profile.interests,
                    'photos': profile.photos,
                    'bio': profile.bio,
                    'location': profile.location,
                    'premium': profile.premium,
                }
            }
            
            return success_response(public_data, "User profile retrieved")
            
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return error_response("Failed to fetch profile", 500)
