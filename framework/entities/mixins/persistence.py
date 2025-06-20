"""
Persistence Mixin - Repository-based Entity Persistence

💾 Clean Architecture Persistence Operations:
This mixin provides entity persistence capabilities using the repository pattern,
integrating with the dependency injection container and persistence manager.
"""

from typing import Optional, Type, List, ClassVar, TYPE_CHECKING
import asyncio
from datetime import datetime

from ...persistence.repositories import (
    PersistenceManager, EntityRepository, QueryOptions, QueryResult,
    QueryFilter, TransactionContext
)

if TYPE_CHECKING:
    from ..lifecycle.entity import Entity

class PersistenceMixin:
    """
    Repository-based persistence operations mixin.
    
    Provides async and sync persistence methods that integrate with
    the StarModel persistence layer and repository pattern.
    """
    
    # Class-level repository cache
    _repository_cache: ClassVar[dict] = {}
    
    async def save(self, ttl: Optional[int] = None, 
                   context: Optional[TransactionContext] = None) -> str:
        """
        Save entity to configured repository.
        
        Args:
            ttl: Time-to-live in seconds (for TTL-enabled backends)
            context: Optional transaction context
            
        Returns:
            Entity ID
        """
        repository = await self._get_repository()
        
        # Set TTL if supported
        if ttl and hasattr(self, '_set_ttl'):
            self._set_ttl(ttl)
        
        # Update timestamps
        now = datetime.now()
        if hasattr(self, 'updated_at'):
            self.updated_at = now
        
        if not hasattr(self, 'created_at') or not self.created_at:
            if hasattr(self, 'created_at'):
                self.created_at = now
        
        return await repository.save(self, context)
    
    async def delete(self, context: Optional[TransactionContext] = None) -> bool:
        """
        Delete entity from repository.
        
        Args:
            context: Optional transaction context
            
        Returns:
            True if deleted, False if not found
        """
        if not hasattr(self, 'id') or not self.id:
            return False
        
        repository = await self._get_repository()
        return await repository.delete(type(self), self.id, context)
    
    async def exists(self, context: Optional[TransactionContext] = None) -> bool:
        """
        Check if entity exists in repository.
        
        Args:
            context: Optional transaction context
            
        Returns:
            True if exists, False otherwise
        """
        if not hasattr(self, 'id') or not self.id:
            return False
        
        repository = await self._get_repository()
        return await repository.exists(type(self), self.id, context)
    
    async def reload(self, context: Optional[TransactionContext] = None) -> bool:
        """
        Reload entity from repository.
        
        Args:
            context: Optional transaction context
            
        Returns:
            True if reloaded, False if not found
        """
        if not hasattr(self, 'id') or not self.id:
            return False
        
        repository = await self._get_repository()
        fresh_entity = await repository.load(type(self), self.id, context)
        
        if fresh_entity:
            # Update current instance with fresh data
            for field_name, field_value in fresh_entity.model_dump().items():
                if hasattr(self, field_name):
                    setattr(self, field_name, field_value)
            return True
        
        return False
    
    # Class methods for entity queries
    @classmethod
    async def load(cls, entity_id: str, 
                   context: Optional[TransactionContext] = None) -> Optional['Entity']:
        """
        Load entity by ID.
        
        Args:
            entity_id: The entity ID to load
            context: Optional transaction context
            
        Returns:
            Entity instance or None if not found
        """
        repository = await cls._get_repository_for_class()
        return await repository.load(cls, entity_id, context)
    
    @classmethod
    async def query(cls, options: QueryOptions, 
                    context: Optional[TransactionContext] = None) -> QueryResult['Entity']:
        """
        Query entities with filtering and sorting.
        
        Args:
            options: Query options (filters, sorting, pagination)
            context: Optional transaction context
            
        Returns:
            Query result with entities and metadata
        """
        repository = await cls._get_repository_for_class()
        return await repository.query(cls, options, context)
    
    @classmethod
    async def count(cls, filters: Optional[List[QueryFilter]] = None,
                    context: Optional[TransactionContext] = None) -> int:
        """
        Count entities matching filters.
        
        Args:
            filters: Optional list of filters
            context: Optional transaction context
            
        Returns:
            Number of matching entities
        """
        repository = await cls._get_repository_for_class()
        return await repository.count(cls, filters, context)
    
    @classmethod
    async def all(cls, limit: Optional[int] = None,
                  context: Optional[TransactionContext] = None) -> QueryResult['Entity']:
        """
        Get all entities of this type.
        
        Args:
            limit: Optional limit on number of entities
            context: Optional transaction context
            
        Returns:
            Query result with all entities
        """
        options = QueryOptions(limit=limit)
        return await cls.query(options, context)
    
    @classmethod
    async def where(cls, **filters) -> QueryResult['Entity']:
        """
        Convenience method for simple equality filters.
        
        Args:
            **filters: Field=value filters
            
        Returns:
            Query result with matching entities
        """
        options = QueryOptions()
        for field, value in filters.items():
            options.equals(field, value)
        
        return await cls.query(options)
    
    @classmethod
    async def save_batch(cls, entities: List['Entity'], 
                         context: Optional[TransactionContext] = None) -> List[str]:
        """
        Save multiple entities in a batch.
        
        Args:
            entities: List of entities to save
            context: Optional transaction context
            
        Returns:
            List of entity IDs
        """
        repository = await cls._get_repository_for_class()
        return await repository.save_batch(entities, context)
    
    @classmethod
    async def delete_batch(cls, entity_ids: List[str],
                           context: Optional[TransactionContext] = None) -> int:
        """
        Delete multiple entities by ID.
        
        Args:
            entity_ids: List of entity IDs to delete
            context: Optional transaction context
            
        Returns:
            Number of entities actually deleted
        """
        repository = await cls._get_repository_for_class()
        return await repository.delete_batch(cls, entity_ids, context)
    
    # Repository access helpers
    async def _get_repository(self) -> EntityRepository:
        """Get repository for this entity instance"""
        return await self._get_repository_for_class()
    
    @classmethod
    async def _get_repository_for_class(cls) -> EntityRepository:
        """Get repository for this entity class"""
        # Check cache first
        class_key = f"{cls.__module__}.{cls.__name__}"
        if class_key in cls._repository_cache:
            return cls._repository_cache[class_key]
        
        # Get from persistence manager
        persistence_manager = cls._get_persistence_manager()
        repository = await persistence_manager.get_repository(cls)
        
        # Cache the repository
        cls._repository_cache[class_key] = repository
        return repository
    
    @classmethod
    def _get_persistence_manager(cls) -> PersistenceManager:
        """Get persistence manager from DI container or create default"""
        try:
            # Try to get from DI container
            from ...infrastructure.dependency_injection.container import get_current_container
            container = get_current_container()
            if container:
                manager = container.get("PersistenceManager")
                # Handle async factory functions
                if asyncio.iscoroutine(manager):
                    loop = asyncio.get_event_loop()
                    return loop.run_until_complete(manager)
                return manager
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not get persistence manager from DI container: {e}")
        
        # Fallback to default manager
        from ...persistence.repositories.manager import create_persistence_manager
        import asyncio
        
        # Create default manager - this should be rare in production
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new task to handle the async manager creation
                future = asyncio.ensure_future(create_persistence_manager())
                # This is a blocking call - not ideal but necessary for sync compatibility
                return loop.run_until_complete(future)
            else:
                return loop.run_until_complete(create_persistence_manager())
        except Exception as e:
            # Last resort - create a minimal manager
            from ...persistence.repositories.manager import PersistenceManager
            return PersistenceManager()
    
    # Synchronous convenience methods (for backwards compatibility)
    def save_sync(self, ttl: Optional[int] = None) -> str:
        """Synchronous save operation"""
        return asyncio.run(self.save(ttl))
    
    def delete_sync(self) -> bool:
        """Synchronous delete operation"""
        return asyncio.run(self.delete())
    
    def exists_sync(self) -> bool:
        """Synchronous exists check"""
        return asyncio.run(self.exists())
    
    @classmethod
    def load_sync(cls, entity_id: str) -> Optional['Entity']:
        """Synchronous load operation"""
        return asyncio.run(cls.load(entity_id))
    
    @classmethod
    def where_sync(cls, **filters) -> QueryResult['Entity']:
        """Synchronous where query"""
        return asyncio.run(cls.where(**filters))

# Legacy compatibility
class EntityPersistenceMixin(PersistenceMixin):
    """Legacy alias for PersistenceMixin"""
    pass

# Export main components
__all__ = ["PersistenceMixin", "EntityPersistenceMixin"]