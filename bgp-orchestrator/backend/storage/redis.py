"""
Redis storage for cache and state management.
"""
import json
from typing import Any, Optional

from redis import Redis


class RedisStorage:
    """
    Redis storage wrapper for cache and state management.
    
    Provides convenient methods for storing BGP data, session state,
    and caching frequently accessed information.
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize Redis storage.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    def get(self, key: str) -> Optional[str]:
        """
        Get value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Value if found, None otherwise
        """
        return self.redis.get(key)

    def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None,
    ) -> bool:
        """
        Set key-value pair.
        
        Args:
            key: Cache key
            value: Value to store
            expire: Expiration time in seconds (optional)
            
        Returns:
            True if successful
        """
        return self.redis.set(key, value, ex=expire)

    def get_json(self, key: str) -> Optional[dict[str, Any]]:
        """
        Get JSON value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Decoded JSON dictionary if found, None otherwise
        """
        value = self.get(key)
        if value:
            return json.loads(value)
        return None

    def set_json(
        self,
        key: str,
        value: dict[str, Any],
        expire: Optional[int] = None,
    ) -> bool:
        """
        Set JSON value.
        
        Args:
            key: Cache key
            value: Dictionary to store
            expire: Expiration time in seconds (optional)
            
        Returns:
            True if successful
        """
        return self.set(key, json.dumps(value), expire=expire)

    def delete(self, key: str) -> bool:
        """
        Delete key.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        return bool(self.redis.delete(key))

    def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists
        """
        return bool(self.redis.exists(key))

    def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment counter.
        
        Args:
            key: Counter key
            amount: Amount to increment by
            
        Returns:
            New counter value
        """
        return self.redis.incrby(key, amount)

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration on key.
        
        Args:
            key: Cache key
            seconds: Expiration time in seconds
            
        Returns:
            True if expiration was set
        """
        return bool(self.redis.expire(key, seconds))

    def keys(self, pattern: str = "*") -> list[str]:
        """
        Get keys matching pattern.
        
        Args:
            pattern: Pattern to match (default: "*")
            
        Returns:
            List of matching keys
        """
        return list(self.redis.keys(pattern))

    def ping(self) -> bool:
        """
        Test Redis connection.
        
        Returns:
            True if connection is active
        """
        try:
            return self.redis.ping()
        except Exception:
            return False

