"""
Persistence Manager and Repository Pattern

Implements the repository pattern to abstract persistence operations
and route entities to appropriate storage backends based on their configuration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.entity import Entity

# Import existing persistence backends
from ..persistence.memory import MemoryEntityPersistence


class RepositoryInterface(ABC):
    """Abstract base class for all repository implementations."""
    
    @abstractmethod
    async def save(self, entity: 'Entity') -> None:
        """Save an entity to the storage backend."""
        pass
    
    @abstractmethod
    async def get(self, entity_class: Type['Entity'], entity_id: str) -> 'Entity':
        """Retrieve an entity by class and ID."""
        pass
    
    @abstractmethod
    async def delete(self, entity_class: Type['Entity'], entity_id: str) -> None:
        """Delete an entity by class and ID."""
        pass
    
    @abstractmethod
    def exists(self, entity_class: Type['Entity'], entity_id: str) -> bool:
        """Check if an entity exists."""
        pass


class MemoryRepository(RepositoryInterface):
    """
    Repository implementation for memory-based storage.
    
    Wraps the existing MemoryEntityPersistence to implement
    the repository interface.
    """
    
    def __init__(self):
        """Initialize the memory repository."""
        self._backend = MemoryEntityPersistence()
    
    async def save(self, entity: 'Entity') -> None:
        """Save an entity to memory storage."""
        # Use the existing synchronous method for now
        # TODO: Make this properly async in Phase 2
        self._backend.save_entity_sync(entity)
    
    async def get(self, entity_class: Type['Entity'], entity_id: str) -> 'Entity':
        """Retrieve an entity from memory storage."""
        # TODO: Implement proper get method
        # For now, this will need to be implemented based on existing patterns
        raise NotImplementedError("Memory repository get() not yet implemented")
    
    async def delete(self, entity_class: Type['Entity'], entity_id: str) -> None:
        """Delete an entity from memory storage."""
        # TODO: Implement delete method
        raise NotImplementedError("Memory repository delete() not yet implemented")
    
    def exists(self, entity_class: Type['Entity'], entity_id: str) -> bool:
        """Check if an entity exists in memory storage."""
        # TODO: Implement exists method
        return False


class PersistenceManager:
    """
    Routes entities to appropriate repositories based on model_config.
    
    This class implements the strategy pattern to select the correct
    repository implementation based on the entity's persistence configuration.
    """
    
    def __init__(self):
        """Initialize the persistence manager with default backends."""
        # Import EntityStore enum from the appropriate location
        # TODO: Import from the correct location once we determine where EntityStore is defined
        
        self._repositories: Dict[str, RepositoryInterface] = {
            'server_memory': MemoryRepository(),
            # TODO: Add other repositories in future phases:
            # 'server_sql': SQLRepository(),     # Phase 1b
            # 'server_redis': RedisRepository(), # Phase 2
        }
        
        self._default_store = 'server_memory'
    
    def for_class(self, entity_class: Type['Entity']) -> RepositoryInterface:
        """
        Get the appropriate repository for an entity class.
        
        Args:
            entity_class: Entity class to get repository for
            
        Returns:
            Repository instance for the entity's configured storage
        """
        # Get store configuration from entity's model_config
        store = getattr(entity_class, 'model_config', {}).get('store', self._default_store)
        
        # Convert EntityStore enum to string if needed
        if hasattr(store, 'value'):
            store = store.value
        
        # Get repository for the specified store
        if store not in self._repositories:
            raise ValueError(f"Unknown storage backend: {store}")
        
        return self._repositories[store]
    
    def register_repository(self, store_name: str, repository: RepositoryInterface) -> None:
        """
        Register a new repository implementation.
        
        This allows plugins to add custom persistence backends.
        
        Args:
            store_name: Name of the storage backend
            repository: Repository implementation
        """
        self._repositories[store_name] = repository
    
    def set_default_store(self, store_name: str) -> None:
        """
        Set the default storage backend.
        
        Args:
            store_name: Name of the default storage backend
        """
        if store_name not in self._repositories:
            raise ValueError(f"Unknown storage backend: {store_name}")
        self._default_store = store_name


# Global persistence manager instance
# This will be configured during application startup
persistence_manager = PersistenceManager()