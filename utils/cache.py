import redis
import json
import logging
import os
from typing import Optional, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Cache TTL settings (in seconds)
CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_MEDIUM = 600  # 10 minutes
CACHE_TTL_LONG = 1800  # 30 minutes

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=5
    )
    # Test connection
    redis_client.ping()
    logger.info(f"✓ Redis connected successfully at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"⚠ Redis connection failed: {str(e)}. Caching will be disabled.")
    redis_client = None


class CacheManager:
    """Manager for Redis caching operations"""
    
    @staticmethod
    def is_available() -> bool:
        """Check if Redis is available"""
        return redis_client is not None
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/error
        """
        if not CacheManager.is_available():
            return None
        
        try:
            value = redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {str(e)}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: int = CACHE_TTL_MEDIUM) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not CacheManager.is_available():
            return False
        
        try:
            redis_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)  # default=str handles datetime, etc.
            )
            logger.debug(f"Cached key '{key}' with TTL {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {str(e)}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """
        Delete a key from cache
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not CacheManager.is_available():
            return False
        
        try:
            redis_client.delete(key)
            logger.debug(f"Deleted cache key '{key}'")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {str(e)}")
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """
        Delete all keys matching a pattern
        
        Args:
            pattern: Pattern to match (e.g., 'user:123:*')
            
        Returns:
            Number of keys deleted
        """
        if not CacheManager.is_available():
            return 0
        
        try:
            keys = redis_client.keys(pattern)
            if keys:
                deleted = redis_client.delete(*keys)
                logger.debug(f"Deleted {deleted} cache keys matching '{pattern}'")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for '{pattern}': {str(e)}")
            return 0
    
    @staticmethod
    def invalidate_user_cache(user_id: str):
        """
        Invalidate all cache entries for a specific user
        
        Args:
            user_id: User ID
        """
        patterns = [
            f"matches:discover:{user_id}:*",
            f"matches:list:{user_id}",
            f"user:profile:{user_id}",
        ]
        
        for pattern in patterns:
            CacheManager.delete_pattern(pattern)
        
        logger.info(f"Invalidated cache for user {user_id}")


def cached(ttl: int = CACHE_TTL_MEDIUM, key_prefix: str = ""):
    """
    Decorator for caching function results
    
    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_result = CacheManager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for {func.__name__}")
                return cached_result
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS for {func.__name__}")
            result = func(*args, **kwargs)
            
            # Cache the result
            CacheManager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Cache key builders
def build_discover_cache_key(user_id: str, limit: int, min_age: Optional[int], 
                              max_age: Optional[int], gender: Optional[str]) -> str:
    """Build cache key for discover matches"""
    return f"matches:discover:{user_id}:{limit}:{min_age}:{max_age}:{gender}"


def build_matches_list_cache_key(user_id: str) -> str:
    """Build cache key for user's matches list"""
    return f"matches:list:{user_id}"


def build_user_profile_cache_key(user_id: str) -> str:
    """Build cache key for user profile"""
    return f"user:profile:{user_id}"
