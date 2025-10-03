import logging
from middleware.auth import clerk_required
from middleware.premium import premium_required
from flask_restful import Resource
from flask import request
from models import db, User, Profile, Match
from utils.response import success_response, error_response
from utils.matching import (
    get_potential_matches,
    generate_match_explanation,
    calculate_compatibility_score
)
from utils.cache import (
    CacheManager,
    build_discover_cache_key,
    build_matches_list_cache_key,
    CACHE_TTL_SHORT,
    CACHE_TTL_MEDIUM
)

logger = logging.getLogger(__name__)


class DiscoverMatchesResource(Resource):
    """Resource for discovering new potential matches"""
    
    @clerk_required
    @premium_required
    def get(self):
        """
        Get AI-powered match suggestions for the current user.
        Returns top 2 matches with AI-generated explanations.
        """
        try:
            user_id = request.user.get('sub')
            
            # Get query parameters for filtering
            limit = int(request.args.get('limit', 2))  # Default 2 for initial matches
            min_age = request.args.get('min_age', type=int)
            max_age = request.args.get('max_age', type=int)
            preferred_gender = request.args.get('gender')
            
            # Build cache key
            cache_key = build_discover_cache_key(
                user_id, limit, min_age, max_age, preferred_gender
            )
            
            # Try to get from cache
            cached_result = CacheManager.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache HIT for discover matches - user: {user_id}")
                return success_response(
                    cached_result,
                    "Matches retrieved successfully (cached)"
                )
            
            logger.info(f"Cache MISS for discover matches - user: {user_id}")
            
            # Get user and profile
            user = User.query.get(user_id)
            if not user:
                return error_response("User not found", 404)
            
            user_profile = Profile.query.filter_by(user_id=user_id).first()
            if not user_profile:
                return error_response("Profile not found", 404)
            
            if user_profile.embedding is None:
                return error_response(
                    "Please complete your profile to get matches",
                    400
                )
            
            # Get potential matches using AI embeddings
            potential_matches = get_potential_matches(
                user_id=user_id,
                limit=limit * 2,  # Get more than needed to filter out existing matches
                min_age=min_age,
                max_age=max_age,
                preferred_gender=preferred_gender
            )
            
            if not potential_matches:
                return success_response(
                    {'matches': []},
                    "No matches found at this time. Check back soon!"
                )
            
            # Filter out users we've already matched/declined
            existing_match_ids = set()
            existing_matches = Match.query.filter(
                db.or_(
                    db.and_(Match.user_id_1 == user_id),
                    db.and_(Match.user_id_2 == user_id)
                )
            ).all()
            
            for match in existing_matches:
                existing_match_ids.add(match.user_id_1)
                existing_match_ids.add(match.user_id_2)
            existing_match_ids.discard(user_id)
            
            # Filter potential matches
            filtered_matches = [
                (profile, score) for profile, score in potential_matches
                if profile.user_id not in existing_match_ids
            ][:limit]
            
            if not filtered_matches:
                return success_response(
                    {'matches': []},
                    "No new matches available right now."
                )
            
            # Generate AI explanations for each match
            matches_data = []
            for match_profile, similarity_score in filtered_matches:
                match_user = User.query.get(match_profile.user_id)
                
                if not match_user:
                    continue
                
                # Generate AI explanation
                ai_explanation = generate_match_explanation(
                    user1_profile=user_profile,
                    user1_name=user.name,
                    user2_profile=match_profile,
                    user2_name=match_user.name,
                    similarity_score=similarity_score
                )
                
                compatibility_score = calculate_compatibility_score(similarity_score)
                
                match_data = {
                    'user_id': match_user.id,
                    'name': match_user.name,
                    'age': match_profile.age,
                    'gender': match_profile.gender,
                    'bio': match_profile.bio,
                    'interests': match_profile.interests.split(', ') if match_profile.interests else [],
                    'photos': match_profile.photos or [],
                    'location': match_profile.location,
                    'compatibility_score': compatibility_score,
                    'ai_explanation': ai_explanation,
                    'distance': None  # Can add distance calculation later
                }
                
                matches_data.append(match_data)
            
            logger.info(f"Generated {len(matches_data)} matches for user {user_id}")
            
            # Cache the result for 5 minutes
            result_data = {'matches': matches_data}
            CacheManager.set(cache_key, result_data, ttl=CACHE_TTL_SHORT)
            logger.info(f"Cached discover matches for user {user_id}")
            
            return success_response(
                result_data,
                f"Found {len(matches_data)} potential matches!"
            )
            
        except Exception as e:
            logger.error(f"Error discovering matches: {str(e)}")
            return error_response("Failed to find matches", 500)


class MatchActionResource(Resource):
    """Resource for acting on matches (like/pass)"""
    
    @clerk_required
    def post(self):
        """
        Create a match action (like or pass).
        If both users like each other, it becomes a matched status.
        """
        try:
            user_id = request.user.get('sub')
            data = request.get_json()
            
            if not data:
                return error_response("No data provided", 400)
            
            target_user_id = data.get('target_user_id')
            action = data.get('action')  # 'like' or 'pass'
            
            if not target_user_id or not action:
                return error_response("target_user_id and action are required", 400)
            
            if action not in ['like', 'pass', 'declined']:
                return error_response("Invalid action. Must be 'like' or 'pass'", 400)
            
            if target_user_id == user_id:
                return error_response("Cannot match with yourself", 400)
            
            # Order user IDs to maintain consistency
            user_id_1, user_id_2 = sorted([user_id, target_user_id])
            
            # Check if match already exists
            existing_match = Match.query.filter_by(
                user_id_1=user_id_1,
                user_id_2=user_id_2
            ).first()
            
            if existing_match:
                # Update existing match
                if action == 'like':
                    # Check if other user also liked
                    if existing_match.match_status == 'pending':
                        # Check who initiated
                        if (user_id == user_id_2 and existing_match.user_id_1 == user_id_1):
                            # Other user liked first, now it's a match!
                            existing_match.match_status = 'matched'
                            logger.info(f"Match created between {user_id_1} and {user_id_2}")
                else:
                    existing_match.match_status = 'declined'
                
                db.session.commit()
                
                # Invalidate cache for both users
                CacheManager.invalidate_user_cache(user_id)
                CacheManager.invalidate_user_cache(target_user_id)
                logger.info(f"Invalidated cache for users {user_id} and {target_user_id}")
                
                return success_response(
                    {
                        'match_id': str(existing_match.id),
                        'status': existing_match.match_status,
                        'is_match': existing_match.match_status == 'matched'
                    },
                    "Match updated successfully"
                )
            
            # Create new match record
            if action == 'like':
                # Get profiles for compatibility score
                user_profile = Profile.query.filter_by(user_id=user_id).first()
                target_profile = Profile.query.filter_by(user_id=target_user_id).first()
                
                if (user_profile and target_profile and 
                    user_profile.embedding is not None and target_profile.embedding is not None):
                    from utils.matching import calculate_cosine_similarity, calculate_compatibility_score
                    similarity = calculate_cosine_similarity(
                        user_profile.embedding,
                        target_profile.embedding
                    )
                    compatibility = calculate_compatibility_score(similarity)
                else:
                    compatibility = 0
                
                new_match = Match(
                    user_id_1=user_id_1,
                    user_id_2=user_id_2,
                    match_status='pending',
                    compatibility_score=compatibility
                )
                db.session.add(new_match)
                db.session.commit()
                
                # Invalidate cache for both users
                CacheManager.invalidate_user_cache(user_id)
                CacheManager.invalidate_user_cache(target_user_id)
                
                logger.info(f"Pending match created: {user_id} likes {target_user_id}")
                
                return success_response(
                    {
                        'match_id': str(new_match.id),
                        'status': 'pending',
                        'is_match': False
                    },
                    "Like sent!"
                )
            else:
                # Pass - create declined record
                new_match = Match(
                    user_id_1=user_id_1,
                    user_id_2=user_id_2,
                    match_status='declined',
                    compatibility_score=0
                )
                db.session.add(new_match)
                db.session.commit()
                
                # Invalidate cache for user
                CacheManager.invalidate_user_cache(user_id)
                
                return success_response(
                    {'status': 'declined'},
                    "Passed on this match"
                )
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating match action: {str(e)}")
            return error_response("Failed to process match action", 500)


class UserMatchesResource(Resource):
    """Resource for getting user's current matches"""
    
    @clerk_required
    def get(self):
        """Get all matched connections for the current user"""
        try:
            user_id = request.user.get('sub')
            
            # Get all matches where status is 'matched'
            matches = Match.query.filter(
                db.and_(
                    db.or_(
                        Match.user_id_1 == user_id,
                        Match.user_id_2 == user_id
                    ),
                    Match.match_status == 'matched'
                )
            ).order_by(Match.created_at.desc()).all()
            
            matches_data = []
            for match in matches:
                # Get the other user's ID
                other_user_id = match.user_id_2 if match.user_id_1 == user_id else match.user_id_1
                
                other_user = User.query.get(other_user_id)
                other_profile = Profile.query.filter_by(user_id=other_user_id).first()
                
                if not other_user or not other_profile:
                    continue
                
                match_data = {
                    'match_id': str(match.id),
                    'user_id': other_user.id,
                    'name': other_user.name,
                    'age': other_profile.age,
                    'photos': other_profile.photos or [],
                    'bio': other_profile.bio,
                    'interests': other_profile.interests.split(', ') if other_profile.interests else [],
                    'location': other_profile.location,
                    'compatibility_score': match.compatibility_score,
                    'ai_explanation': match.ai_explanation,
                    'matched_at': match.created_at.isoformat() if match.created_at else None
                }
                
                matches_data.append(match_data)
            
            return success_response(
                {'matches': matches_data, 'total': len(matches_data)},
                "Matches retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error fetching matches: {str(e)}")
            return error_response("Failed to fetch matches", 500)


class MatchedUsersResource(Resource):
    """Resource for getting list of matched users for chat"""
    
    @clerk_required
    def get(self):
        """
        Get all users that the current user has matched with.
        Returns list of matched users with their details.
        """
        try:
            user_id = request.user.get('sub')
            
            # Get all matches where status is 'matched'
            matches = Match.query.filter(
                ((Match.user_id_1 == user_id) | (Match.user_id_2 == user_id)),
                Match.match_status == 'matched'
            ).all()
            
            matches_data = []
            for match in matches:
                # Determine the other user in the match
                other_user_id = match.user_id_2 if match.user_id_1 == user_id else match.user_id_1
                other_user = User.query.get(other_user_id)
                other_profile = Profile.query.filter_by(user_id=other_user_id).first()
                
                if not other_user or not other_profile:
                    continue
                
                match_data = {
                    'id': str(match.id),
                    'user_id': other_user_id,
                    'name': other_user.name,
                    'age': other_profile.age,
                    'photos': other_profile.photos or [],
                    'bio': other_profile.bio,
                    'location': other_profile.location,
                    'compatibility_score': match.compatibility_score or 0,
                    'matched_at': match.created_at.isoformat() if match.created_at else None
                }
                
                matches_data.append(match_data)
            
            # Sort by most recent matches first
            matches_data.sort(key=lambda x: x['matched_at'] or '', reverse=True)
            
            return success_response(
                {'matches': matches_data, 'total': len(matches_data)},
                "Matched users retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error fetching matched users: {str(e)}")
            return error_response("Failed to fetch matched users", 500)


class MatchDetailResource(Resource):
    """Resource for getting specific match details"""
    
    @clerk_required
    def get(self, match_id):
        """
        Get details of a specific match by match ID.
        Used for loading chat conversations.
        """
        try:
            user_id = request.user.get('sub')
            
            # Get the match
            match = Match.query.get(match_id)
            
            if not match:
                return error_response("Match not found", 404)
            
            # Verify user is part of this match
            if match.user_id_1 != user_id and match.user_id_2 != user_id:
                return error_response("Unauthorized access to this match", 403)
            
            # Verify match status is 'matched'
            if match.match_status != 'matched':
                return error_response("This is not an active match", 400)
            
            # Get the other user's details
            other_user_id = match.user_id_2 if match.user_id_1 == user_id else match.user_id_1
            other_user = User.query.get(other_user_id)
            other_profile = Profile.query.filter_by(user_id=other_user_id).first()
            
            if not other_user or not other_profile:
                return error_response("User profile not found", 404)
            
            match_data = {
                'id': other_user_id,
                'name': other_user.name,
                'age': other_profile.age,
                'photos': other_profile.photos or [],
                'bio': other_profile.bio,
                'location': other_profile.location,
                'compatibility_score': match.compatibility_score or 0
            }
            
            return success_response(match_data, "Match details retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error fetching match details: {str(e)}")
            return error_response("Failed to fetch match details", 500)