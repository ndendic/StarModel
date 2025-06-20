"""
Persistence Service - Entity Persistence Operations

💾 Clean Persistence Interface:
This service handles all persistence operations for entities through dependency injection,
eliminating the need for persistence mixins and providing a clean, testable interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from ..lifecycle.entity import Entity

from ...persistence.repositories.interface import EntityRepository
from ...persistence.repositories.manager import PersistenceManager


class PersistenceService(ABC):
    """
    Abstract interface for entity persistence operations.
    
    This service is injected into entities to handle all persistence concerns,
    keeping the entity focused on business logic.
    """
    
    @abstractmethod
    async def save(self, entity: 'Entity', **kwargs) -> str:
        """Save an entity and return its ID"""
        pass
    
    @abstractmethod
    async def load(self, entity_class: Type['Entity'], entity_id: str) -> Optional['Entity']:
        """Load an entity by ID"""
        pass
    
    @abstractmethod
    async def delete(self, entity_class: Type['Entity'], entity_id: str) -> bool:
        """Delete an entity by ID"""
        pass
    
    @abstractmethod
    async def exists(self, entity_class: Type['Entity'], entity_id: str) -> bool:
        """Check if an entity exists"""
        pass
    
    @abstractmethod
    async def list_all(self, entity_class: Type['Entity'], limit: int = 100) -> List['Entity']:
        """List all entities of a type"""
        pass
    
    @abstractmethod
    def generate_id(self) -> str:
        """Generate a unique ID for a new entity"""
        pass
    
    @abstractmethod
    async def get_repository(self, entity_class: Type['Entity']) -> EntityRepository:
        """Get the repository for an entity class"""
        pass


class EntityPersistenceService(PersistenceService):
    """
    Default implementation of persistence service using the repository pattern.
    
    This service coordinates with the persistence manager to handle entity
    storage operations across different backends.
    """
    
    def __init__(self, persistence_manager: PersistenceManager):
        self.persistence_manager = persistence_manager
        self._repositories_cache: Dict[Type, EntityRepository] = {}
    
    async def save(self, entity: 'Entity', **kwargs) -> str:
        """Save an entity through the appropriate repository"""
        # Ensure entity has an ID
        if not entity.id:
            entity.id = self.generate_id()
        
        # Update timestamp
        entity.updated_at = datetime.now()
        if not entity.created_at:
            entity.created_at = entity.updated_at
        
        # Get repository and save
        repository = await self.get_repository(type(entity))
        entity_id = await repository.save(entity, **kwargs)
        
        return entity_id
    
    async def load(self, entity_class: Type['Entity'], entity_id: str) -> Optional['Entity']:
        """Load an entity by ID"""
        repository = await self.get_repository(entity_class)
        return await repository.load(entity_class, entity_id)
    
    async def delete(self, entity_class: Type['Entity'], entity_id: str) -> bool:
        """Delete an entity by ID"""
        repository = await self.get_repository(entity_class)
        return await repository.delete(entity_class, entity_id)
    
    async def exists(self, entity_class: Type['Entity'], entity_id: str) -> bool:
        """Check if an entity exists"""
        repository = await self.get_repository(entity_class)
        return await repository.exists(entity_class, entity_id)
    
    async def list_all(self, entity_class: Type['Entity'], limit: int = 100) -> List['Entity']:
        """List all entities of a type"""
        repository = await self.get_repository(entity_class)
        
        from ...persistence.repositories.interface import QueryOptions
        options = QueryOptions(limit=limit)
        result = await repository.query(entity_class, options)
        
        return result.entities
    
    def generate_id(self) -> str:
        """Generate a unique ID for a new entity"""
        return str(uuid.uuid4())
    
    async def get_repository(self, entity_class: Type['Entity']) -> EntityRepository:
        """Get the repository for an entity class with caching"""
        if entity_class not in self._repositories_cache:
            repository = await self.persistence_manager.get_repository(entity_class)
            self._repositories_cache[entity_class] = repository
        
        return self._repositories_cache[entity_class]
    
    async def cleanup_cache(self):
        """Clear the repository cache"""
        self._repositories_cache.clear()


class InMemoryPersistenceService(PersistenceService):
    """
    Simple in-memory persistence service for testing.
    
    This implementation stores entities in memory without any external dependencies,
    making it perfect for unit tests and development.
    """
    
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}  # {entity_class_name: {id: entity}}
    
    def _get_storage_key(self, entity_class: Type) -> str:
        """Get storage key for entity class"""
        return f"{entity_class.__module__}.{entity_class.__name__}"
    
    def _get_entity_storage(self, entity_class: Type) -> Dict[str, Any]:
        """Get storage dict for entity class"""
        key = self._get_storage_key(entity_class)
        if key not in self._storage:
            self._storage[key] = {}
        return self._storage[key]
    
    async def save(self, entity: 'Entity', **kwargs) -> str:
        """Save entity to memory"""
        if not entity.id:
            entity.id = self.generate_id()
        
        entity.updated_at = datetime.now()
        if not entity.created_at:
            entity.created_at = entity.updated_at
        
        storage = self._get_entity_storage(type(entity))
        storage[entity.id] = entity
        
        return entity.id
    
    async def load(self, entity_class: Type['Entity'], entity_id: str) -> Optional['Entity']:
        """Load entity from memory"""
        storage = self._get_entity_storage(entity_class)
        return storage.get(entity_id)
    
    async def delete(self, entity_class: Type['Entity'], entity_id: str) -> bool:
        """Delete entity from memory"""
        storage = self._get_entity_storage(entity_class)
        if entity_id in storage:
            del storage[entity_id]
            return True
        return False
    
    async def exists(self, entity_class: Type['Entity'], entity_id: str) -> bool:
        """Check if entity exists in memory"""
        storage = self._get_entity_storage(entity_class)
        return entity_id in storage
    
    async def list_all(self, entity_class: Type['Entity'], limit: int = 100) -> List['Entity']:
        """List all entities from memory"""
        storage = self._get_entity_storage(entity_class)
        entities = list(storage.values())
        return entities[:limit]
    
    def generate_id(self) -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4())
    
    async def get_repository(self, entity_class: Type['Entity']) -> EntityRepository:
        """This implementation doesn't use repositories"""
        raise NotImplementedError("InMemoryPersistenceService doesn't use repositories")
    
    def clear_all(self):
        """Clear all stored entities (for testing)"""
        self._storage.clear()


# Export main components
__all__ = [
    "PersistenceService", "EntityPersistenceService", "InMemoryPersistenceService"
]