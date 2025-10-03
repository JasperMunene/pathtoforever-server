import os
import logging
import google.generativeai as genai
from typing import Optional, List

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")


def generate_profile_embedding(bio: str, interests: str) -> Optional[List[float]]:
    """
    Generate an embedding vector for a user profile using Gemini.
    
    Args:
        bio: User's bio text
        interests: Comma-separated interests string
        
    Returns:
        List of floats representing the embedding vector (1536 dimensions)
        or None if embedding generation fails
    """
    if not GEMINI_API_KEY:
        logger.error("Cannot generate embedding: GEMINI_API_KEY not configured")
        return None
    
    try:
        # Combine bio and interests into a single text for embedding
        profile_text = f"Bio: {bio or 'No bio provided'}\nInterests: {interests or 'No interests'}"
        
        # Generate embedding using Gemini's embedding model
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=profile_text,
            task_type="retrieval_document",
            title="Dating Profile"
        )
        
        embedding = result['embedding']
        
        logger.info(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return None


def generate_query_embedding(query_text: str) -> Optional[List[float]]:
    """
    Generate an embedding for a search query.
    
    Args:
        query_text: The search query text
        
    Returns:
        List of floats representing the embedding vector
        or None if embedding generation fails
    """
    if not GEMINI_API_KEY:
        logger.error("Cannot generate embedding: GEMINI_API_KEY not configured")
        return None
    
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query_text,
            task_type="retrieval_query"
        )
        
        embedding = result['embedding']
        logger.info(f"Generated query embedding with {len(embedding)} dimensions")
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating query embedding: {str(e)}")
        return None
