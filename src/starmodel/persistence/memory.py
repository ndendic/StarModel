"""
StarModel Persistence Layer - Memory Backend

In-memory entity persistence implementation for development and testing.
"""

import time
from typing import Dict, Any, Optional, TYPE_CHECKING

from .base import EntityPersistenceBackend

if TYPE_CHECKING:
    from ..core.entity import Entity

class MemoryRepo(EntityPersistenceBackend):
    """
    In-memory entity persistence implementation (Singleton).
    
    Provides fast persistence for development and testing.
    Data is lost when the application restarts.
    Uses singleton pattern to ensure single shared instance.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize memory persistence backend (only once)."""
        if not self._initialized:
            self._data: Dict[str, Dict[str, Any]] = {}
            self._expiry: Dict[str, float] = {}
            MemoryRepo._initialized = True
    
    
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
    
    def load_entity_sync(self, key: str) -> Optional['Entity']:
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

# Convenience function to get singleton instance
def get_memory_persistence() -> MemoryRepo:
    """Get the singleton memory persistence instance."""
    return MemoryRepo()