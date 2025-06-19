"""
PersistenceMixin: Persistence operations without base model dependencies.

This mixin provides persistence functionality that can be mixed into
any base model class.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...persistence import EntityPersistenceBackend


class PersistenceMixin:
    """
    Persistence operations mixin.
    
    Provides save, delete, and exists methods that work with any
    persistence backend through the entity's configuration.
    """
    
    def save(self, ttl: Optional[int] = None) -> bool:
        """Save entity to configured backend."""
        return self.persistence_backend.save_entity_sync(self, ttl)
        
    def delete(self) -> bool:
        """Delete entity from configured backend."""
        return self.persistence_backend.delete_entity_sync(self.id)
    
    def exists(self) -> bool:
        """Check if entity exists in configured backend."""
        return self.persistence_backend.exists_sync(self.id)
    
    @classmethod
    def get(cls, req, **kwargs):
        """Get cached entity or create new."""
        entity_id = cls._get_id(req, **kwargs)
        
        # Try to get from persistence backend
        if hasattr(cls, '_persistence_backend_class'):
            backend = cls._persistence_backend_class()
            cached = backend.load_entity_sync(entity_id)        
            if cached and isinstance(cached, cls):
                return cached
                
        return cls(req, id=entity_id, **kwargs)