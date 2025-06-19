"""
Fixed SQLEntity implementation without mixin inheritance.

This version copies essential functionality from mixins directly into the class
to avoid metaclass conflicts with SQLModel.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
import asyncio
import json

from sqlmodel import SQLModel, Field
from fasthtml.common import *
from pydantic import ConfigDict

from .signals import SignalDescriptor, EventMethodDescriptor
from ..persistence import SQLModelBackend
from .events import event

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SQLEntity(SQLModel, table=True):
    """SQL-backed entity without mixin inheritance to avoid metaclass conflicts."""
    
    # SQLAlchemy table configuration
    __table_args__ = {'extend_existing': True}

    # Pydantic model configuration (for validation/serialization)
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        validate_assignment=True,
        json_encoders={datetime: lambda dt: dt.isoformat()}
    )
    
    # StarModel configuration (underscore attributes - not Pydantic fields)
    _use_namespace: bool = True
    _auto_persist: bool = True
    _sync_with_client: bool = True
    _namespace: Optional[str] = None
    _persistence_backend = SQLModelBackend()
    
    # Define id field for SQLModel
    id: str = Field(primary_key=True)

    # Copy essential properties from EntityMixin
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
        return self._persistence_backend
    
    @property
    def signals(self) -> Dict[str, Any]:
        """Get signals for this entity."""
        if self.use_namespace:
            return {self.namespace: self.model_dump()}
        else:
            return self.model_dump()

    # Copy essential methods from PersistenceMixin
    def save(self, ttl: Optional[int] = None) -> "SQLEntity":
        """Save entity to configured backend."""
        return self.persistence_backend.save_entity_sync(self, ttl)
        
    def delete(self) -> None:
        """Delete entity from configured backend."""
        return self.persistence_backend.delete_entity_sync(self)
    
    def exists(self) -> bool:
        """Check if entity exists in configured backend."""
        return self.persistence_backend.exists_sync(self.id)

    # Copy essential utility methods
    def __ft__(self):
        """Render with data-signals attributes."""
        signals = json.dumps(self.signals)
        return Div({"data-signals": signals}, id=f"{self.namespace}")

    def set_from_request(self, req: Request, **kwargs) -> 'SQLEntity':
        """Initialize entity instance with Datastar payload."""
        from .events import datastar_from_queryParams
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
        """Generate deterministic entity ID."""
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
            return cls.get_session_id(req, **kwargs)

    @classmethod
    def get(cls, req, id: Any = None, alt_key: str = None, **kwargs) -> 'SQLEntity':
        """Get cached entity or create new."""
        if id is None:
            entity_id = cls._get_id(req, **kwargs)
        else:
            entity_id = id
        
        # Try to get from persistence backend
        cached = cls._persistence_backend.load_entity_sync(cls, entity_id, alt_key)        
        if cached and isinstance(cached, cls):
            return cached
        
        return cls(id=entity_id, **kwargs)

    # Class initialization methods
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        
        # Create signal descriptors for all model fields
        for field_name in cls.model_fields:
            setattr(cls, f"{field_name}_signal", SignalDescriptor(field_name))
        for field_name in cls.model_computed_fields:
            setattr(cls, f"{field_name}_signal", SignalDescriptor(field_name))
        
        # Create URL generator methods for @event decorated methods
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_event_info'):
                url_generator = EventMethodDescriptor(attr_name, cls.__name__, attr)
                setattr(cls, attr_name, url_generator)
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        if cls._namespace is None and cls._use_namespace:
            cls._namespace = cls.__name__

    # SQL-specific methods
    @classmethod
    def all(cls) -> List["SQLEntity"]:
        return cls._persistence_backend.all_records(cls)

    @classmethod
    def total_records(cls) -> int:
        return len(cls.all())

    @classmethod
    def search(cls, search_value: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        return cls._persistence_backend.search(cls, search_value=search_value, **kwargs)

    @classmethod
    def filter(cls, **kwargs) -> List[Dict[str, Any]]:
        return cls._persistence_backend.filter(model=cls, **kwargs)

    @classmethod
    def update_record(cls, id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        return cls._persistence_backend.update_record(cls, id, data)

    @classmethod
    def delete_record(cls, id: Any) -> None:
        return cls._persistence_backend.delete_record(cls, id)

    # Default event methods that can be overridden
    @event
    async def live(self, heartbeat: float = 15):
        """Live event for real-time updates."""
        while True:
            yield self.signals
            await asyncio.sleep(heartbeat)

    @event
    async def poll(self):
        """Poll event for periodic updates."""
        pass

    @event
    async def sync(self, datastar):    
        """Sync event for client synchronization."""
        self.set_from_request(datastar)
        return self.signals