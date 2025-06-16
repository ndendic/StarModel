"""
StarModel Persistence Layer - Base Classes

This module provides abstract interfaces for entity persistence backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import StrEnum

class EntityStore(StrEnum):
    """Enumeration of entity storage mechanisms supported by StarModel."""
    CLIENT_SESSION = "client_session"    # Datastar sessionStorage
    CLIENT_LOCAL = "client_local"        # Datastar localStorage
    SERVER_MEMORY = "server_memory"      # MemoryEntityPersistence
    CUSTOM = "custom"    

class EntityPersistenceBackend(ABC):
    """
    Abstract base class for entity persistence backends.
    
    Implementations must provide methods for saving, loading, and managing
    entity data with optional TTL support.
    """
    
    @abstractmethod
    async def save_entity(self, key: str, entity_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Save entity data to the persistence backend.
        
        Args:
            key: Unique identifier for the entity
            entity_data: Entity data to persist (JSON-serializable)
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def load_entity(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Load entity data from the persistence backend.
        
        Args:
            key: Unique identifier for the entity
            
        Returns:
            Entity data dictionary if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete_entity(self, key: str) -> bool:
        """
        Delete entity data from the persistence backend.
        
        Args:
            key: Unique identifier for the entity
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if entity exists in the persistence backend.
        
        Args:
            key: Unique identifier for the entity
            
        Returns:
            True if entity exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Clean up expired entity entries.
        
        Returns:
            Number of entries cleaned up
        """
        pass
    
    def save_entity_sync(self, key: str, entity_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Save entity to persistence backend (synchronous version)."""
        raise NotImplementedError("save_entity_sync is not implemented")
    
    def load_entity_sync(self, key: str) -> Optional[Dict[str, Any]]:
        """Load entity from persistence backend (synchronous version)."""   
        raise NotImplementedError("load_entity_sync is not implemented")
    
    def delete_entity_sync(self, key: str) -> bool:
        """Delete entity from persistence backend (synchronous version)."""
        raise NotImplementedError("delete_entity_sync is not implemented")

    def exists_sync(self, key: str) -> bool:
        """Check if entity exists in persistence backend (synchronous version)."""
        raise NotImplementedError("exists_sync is not implemented")
    
    def cleanup_expired_sync(self) -> int:
        """Clean up expired entity entries (synchronous version)."""
        raise NotImplementedError("cleanup_expired_sync is not implemented")