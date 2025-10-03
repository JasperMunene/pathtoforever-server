import os
import logging
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, not_
from models import db, Profile, User

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def get_potential_matches(
    user_id: str,
    limit: int = 10,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    preferred_gender: Optional[str] = None
) -> List[Tuple[Profile, float]]:
    """
    Find potential matches for a user using embedding similarity.
    
    Args:
        user_id: The user's ID
        limit: Maximum number of matches to return
        min_age: Minimum age filter (optional)
        max_age: Maximum age filter (optional)
        preferred_gender: Preferred gender filter (optional)
        
    Returns:
        List of tuples containing (Profile, similarity_score)
    """
    try:
        # Get the user's profile
        user_profile = Profile.query.filter_by(user_id=user_id).first()
        
        if not user_profile or user_profile.embedding is None:
            logger.warning(f"User {user_id} has no profile or embedding")
            return []
        
        # Build the query with filters
        query = Profile.query.filter(
            Profile.user_id != user_id,  # Exclude self
            Profile.embedding.isnot(None)  # Must have embedding
        )
        
        # Apply age filters
        if min_age is not None:
            query = query.filter(Profile.age >= min_age)
        if max_age is not None:
            query = query.filter(Profile.age <= max_age)
        
        # Apply gender filter
        if preferred_gender:
            query = query.filter(Profile.gender == preferred_gender)
        
        # Get all potential candidates
        candidates = query.all()
        
        if len(candidates) == 0:
            logger.info(f"No candidates found for user {user_id}")
            return []
        
        # Calculate similarity scores using cosine similarity
        matches_with_scores = []
        
        for candidate in candidates:
            if candidate.embedding is None:
                continue
                
            # Calculate cosine similarity (1 - cosine_distance)
            # pgvector stores embeddings, we can calculate similarity in Python
            try:
                similarity = calculate_cosine_similarity(
                    user_profile.embedding, 
                    candidate.embedding
                )
                matches_with_scores.append((candidate, similarity))
            except Exception as e:
                logger.error(f"Error calculating similarity for candidate {candidate.user_id}: {str(e)}")
                continue
        
        # Sort by similarity score (highest first)
        matches_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top matches
        return matches_with_scores[:limit]
        
    except Exception as e:
        logger.error(f"Error finding matches for user {user_id}: {str(e)}")
        return []


def calculate_cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    import numpy as np
    
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    # Cosine similarity = dot product / (norm1 * norm2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    return float(similarity)


def generate_match_explanation(
    user1_profile: Profile,
    user1_name: str,
    user2_profile: Profile,
    user2_name: str,
    similarity_score: float
) -> str:
    """
    Use Gemini LLM to generate an AI explanation for why two profiles match.
    
    Args:
        user1_profile: First user's profile
        user1_name: First user's name
        user2_profile: Second user's profile
        user2_name: Second user's name
        similarity_score: The embedding similarity score
        
    Returns:
        AI-generated explanation string
    """
    if not GEMINI_API_KEY:
        return "AI matching is currently unavailable."
    
    try:
        # Prepare profile information
        user1_info = f"""
        Name: {user1_name}
        Age: {user1_profile.age}
        Gender: {user1_profile.gender}
        Interests: {user1_profile.interests or 'Not specified'}
        Bio: {user1_profile.bio or 'No bio provided'}
        Location: {user1_profile.location or 'Not specified'}
        """
        
        user2_info = f"""
        Name: {user2_name}
        Age: {user2_profile.age}
        Gender: {user2_profile.gender}
        Interests: {user2_profile.interests or 'Not specified'}
        Bio: {user2_profile.bio or 'No bio provided'}
        Location: {user2_profile.location or 'Not specified'}
        """
        
        # Create prompt for Gemini
        prompt = f"""You are an expert matchmaker for a dating app. Based on the following two user profiles, explain why they would be a great match. Focus on shared interests, compatible personalities, and potential for a meaningful connection.

Profile 1:
{user1_info}

Profile 2:
{user2_info}

Compatibility Score: {similarity_score * 100:.1f}%

Generate a warm, engaging, and concise explanation (2-3 sentences, max 150 characters) about why these two people would be a great match. Focus on specific shared interests or complementary qualities. Make it personal and conversational.

Explanation:"""

        # Generate explanation using Gemini
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)
        explanation = response.text.strip()
        
        # Limit to reasonable length
        if len(explanation) > 200:
            explanation = explanation[:197] + "..."
        
        logger.info(f"Generated match explanation for {user1_name} and {user2_name}")
        return explanation
        
    except Exception as e:
        logger.error(f"Error generating match explanation: {str(e)}")
        return f"You both share similar interests and values, making you a great potential match!"


def calculate_compatibility_score(similarity: float) -> int:
    """
    Convert similarity score (0-1) to compatibility percentage (0-100)
    
    Args:
        similarity: Cosine similarity score (0-1)
        
    Returns:
        Compatibility score as integer percentage (0-100)
    """
    # Convert to percentage and round
    score = int(similarity * 100)
    
    # Ensure it's within bounds
    return max(0, min(100, score))
