"""
StarModel Persistence Layer - Base Classes

This module provides abstract interfaces for entity persistence backends.
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.entity import Entity

class EntityPersistenceBackend(ABC):
    """
    Abstract base class for entity persistence backends.
    
    Implementations must provide methods for saving, loading, and managing
    entity instances with optional TTL support.
    """
    
    @abstractmethod
    def save_entity_sync(self, entity: 'Entity', ttl: Optional[int] = None) -> bool:
        """
        Save entity instance to the persistence backend.
        
        Args:
            entity: Entity instance to persist
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def load_entity_sync(self, entity_id: str) -> Optional['Entity']:
        """
        Load entity instance from the persistence backend.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            Entity instance if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete_entity_sync(self, entity_id: str) -> bool:
        """
        Delete entity from the persistence backend.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def exists_sync(self, entity_id: str) -> bool:
        """
        Check if entity exists in the persistence backend.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            True if entity exists, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup_expired_sync(self) -> int:
        """
        Clean up expired entity entries.
        
        Returns:
            Number of entries cleaned up
        """
        pass