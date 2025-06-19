"""
EntityMixin: Core entity functionality without base model dependencies.

This mixin provides all the essential entity functionality that can be
mixed into any base model class (BaseModel, SQLModel, etc.).
"""

import asyncio
import json
from typing import Any, Dict, Optional
from datetime import datetime

from fasthtml.common import *
from ..signals import SignalDescriptor, EventMethodDescriptor
from ...persistence import MemoryRepo, EntityPersistenceBackend


class EntityMixin:
    """
    Core entity functionality mixin.
    
    Provides configuration management, signals, event handling, and utility methods
    without depending on any specific base model class.
    """
    
    # Configuration as class attributes (underscore prevents Pydantic field detection)
    _use_namespace: bool = True
    _auto_persist: bool = True
    _sync_with_client: bool = True
    _namespace: Optional[str] = None
    _persistence_backend_class = MemoryRepo  # Store class, not instance
    
    @property
    def namespace(self):
        """Get the namespace for this entity instance."""
        return self._namespace or self.__class__.__name__
    
    @property
    def use_namespace(self):
        """Get the use_namespace setting for this entity instance."""
        return self._use_namespace

    @property
    def sync_with_client(self):
        """Get the sync_with_client setting for this entity instance."""
        return self._sync_with_client
    
    @property
    def auto_persist(self):
        """Get the auto_persist setting for this entity instance."""
        return self._auto_persist
    
    @property
    def persistence_backend(self):
        """Get the persistence backend for this entity instance."""
        # Lazy initialization to avoid pickling issues
        return self._persistence_backend_class()
    
    @property
    def signals(self) -> Dict[str, Any]:
        """Get signals for this entity."""
        if self.use_namespace:
            return {self.namespace: self.model_dump()}
        else:
            return self.model_dump()

    def Poll(self, heartbeat: float = 0):
        """Create a polling component for real-time updates."""
        return Div(
            {"data-on-online__window": self.sync(self.signals), 
             f"data-on-interval__duration.{heartbeat}s.leading": self.poll()}, 
            id=f"{self.namespace}"
        )

    def set_from_request(self, req: Request, **kwargs) -> 'EntityMixin':
        """Initialize entity instance with Datastar payload."""
        # Import here to avoid circular dependency
        from ..events import datastar_from_queryParams
        datastar = datastar_from_queryParams(req)    
        for f in self.__class__.model_fields.keys():      
            fns = self.__class__.__name__ + "." + f  
            if f in datastar:
                setattr(self, f, datastar[f])
            elif fns in datastar:
                setattr(self, f, datastar[fns])
        return self
    
    def _sync_from_client(self, req: Request):
        """Sync entity with client-side changes using datastar payload."""
        if req and self.sync_with_client:
            self.set_from_request(req)
    
    @classmethod
    def get_session_id(cls, req: Request, **kwargs) -> str:
        """Generate deterministic entity ID. Override in subclasses for custom logic."""
        # Default: use class name + session-based ID
        if req and hasattr(req, 'cookies'):
            session_id = req.cookies.get('session_', 'default')
        else:
            session_id = 'default'
        return f"{cls.__name__.lower()}_{session_id[:100]}"
    
    @classmethod
    def _get_id(cls, req: Request, call_default_factory=True, **kwargs) -> str:
        """Get entity ID from request or generate default."""
        try:
            from pydantic_core import PydanticUndefined
            id = cls.model_fields['id'].get_default(call_default_factory=call_default_factory)
            if id is PydanticUndefined:
                return cls.get_session_id(req, **kwargs)
            return id
        except (KeyError, AttributeError):
            # Fallback if model_fields doesn't exist or id field not found
            return cls.get_session_id(req, **kwargs)
    
    def __ft__(self):
        """Render with data-signals attributes."""
        signals = json.dumps(self.signals)
        return Div({"data-signals": signals}, id=f"{self.namespace}")

    # Default event methods that subclasses can override
    async def live(self, heartbeat: float = 15):
        """Live event for real-time updates."""
        while True:
            yield self.signals
            await asyncio.sleep(heartbeat)

    async def poll(self):
        """Poll event for periodic updates."""
        pass

    async def sync(self, datastar):    
        """Sync event for client synchronization."""
        self.set_from_request(datastar)
        return self.signals