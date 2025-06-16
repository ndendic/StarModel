"""
StarModel Persistence Layer - Memory Backend

In-memory entity persistence implementation for development and testing.
"""

import time
from typing import Dict, Any, Optional

from .base import EntityPersistenceBackend

class MemoryEntityPersistence(EntityPersistenceBackend):
    """
    In-memory entity persistence implementation.
    
    Provides fast persistence for development and testing.
    Data is lost when the application restarts.
    """
    
    def __init__(self):
        """Initialize memory persistence backend."""
        self._data: Dict[str, Dict[str, Any]] = {}
        self._expiry: Dict[str, float] = {}
    
    async def save_entity(self, key: str, entity_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Save entity to memory with optional TTL."""
        return self.save_entity_sync(key, entity_data, ttl)
    
    async def load_entity(self, key: str) -> Optional[Dict[str, Any]]:
        """Load entity from memory."""
        return self.load_entity_sync(key)
    
    async def delete_entity(self, key: str) -> bool:
        """Delete entity from memory."""
        return self.delete_entity_sync(key)
    
    async def exists(self, key: str) -> bool:
        """Check if entity exists in memory."""
        return self.exists_sync(key)
    
    async def cleanup_expired(self) -> int:
        """Clean up expired entity entries from memory."""
        return self.cleanup_expired_sync()
    
    def save_entity_sync(self, entity, ttl: Optional[int] = None) -> bool:
        """Save entity to memory with optional TTL."""
        try:
            key = entity.id
            self._data[key] = entity            
            if ttl:
                self._expiry[key] = time.time() + ttl
            elif key in self._expiry:
                del self._expiry[key]
            
            return True
            
        except Exception as e:
            print(f"Error saving entity to memory: {e}")
            return False
    
    def load_entity_sync(self, key: str) -> Optional[Dict[str, Any]]:
        """Load entity from memory."""
        try:
            # Check if expired
            if key in self._expiry and time.time() > self._expiry[key]:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return None
            
            return self._data.get(key)
            
        except Exception as e:
            print(f"Error loading entity from memory: {e}")
            return None
    
    def delete_entity_sync(self, key: str) -> bool:
        """Delete entity from memory."""
        try:
            existed = key in self._data
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return existed
            
        except Exception as e:
            print(f"Error deleting entity from memory: {e}")
            return False
    
    def exists_sync(self, key: str) -> bool:
        """Check if entity exists in memory."""
        try:
            # Check if expired
            if key in self._expiry and time.time() > self._expiry[key]:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return False
            
            return key in self._data
            
        except Exception as e:
            print(f"Error checking entity existence in memory: {e}")
            return False
    
    def cleanup_expired_sync(self) -> int:
        """Clean up expired entity entries from memory."""
        try:
            current_time = time.time()
            expired_keys = [
                key for key, expiry_time in self._expiry.items()
                if current_time > expiry_time
            ]
            
            for key in expired_keys:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
            
            return len(expired_keys)
            
        except Exception as e:
            print(f"Error cleaning up expired entities: {e}")
            return 0

# Global instance for backward compatibility
memory_persistence = MemoryEntityPersistence()