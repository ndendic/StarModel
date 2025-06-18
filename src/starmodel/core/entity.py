import inspect
import asyncio
import json
from typing import Any, Dict, Optional

from fasthtml.common import *
from pydantic import BaseModel, Field, ConfigDict
from pydantic_core import PydanticUndefined

from ..persistence import MemoryRepo, EntityPersistenceBackend
from .signals import SignalModelMeta

datastar_script = Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0-beta.11/bundles/datastar.js", type="module")

class EntityConfig(ConfigDict):
    """Configuration for all entity classes."""
    namespace: str | None
    use_namespace: bool
    auto_persist: bool
    persistence_backend: EntityPersistenceBackend
    sync_with_client: bool
    ttl: Optional[int]

class Entity(BaseModel, metaclass=SignalModelMeta):
    """Base class for all entity classes."""
    model_config = EntityConfig(arbitrary_types_allowed=True,
                                use_namespace=True,
                                auto_persist=True,
                                persistence_backend=MemoryRepo(),
                                sync_with_client=True)

    id: str = Field(primary_key=True)

    @classmethod
    def _get_config_value(cls, key: str, default=None):
        """Get configuration value from model_config."""
        return cls.model_config.get(key, default)
    
    @classmethod
    def _set_config_value(cls, key: str, value: Any):
        """Set configuration value in model_config."""
        cls.model_config[key] = value
    
    @property
    def namespace(self):
        """Get the namespace for this entity instance."""
        return self.__class__._get_config_value("namespace", None)
    
    @property
    def use_namespace(self):
        """Get the use_namespace setting for this entity instance."""
        return self.__class__._get_config_value("use_namespace", True)

    
    @property
    def sync_with_client(self):
        """Get the sync_with_client setting for this entity instance."""
        return self.__class__._get_config_value("sync_with_client", True)
    
    @property
    def auto_persist(self):
        """Get the auto_persist setting for this entity instance."""
        return self.__class__._get_config_value("auto_persist", True)
    
    @property
    def persistence_backend(self):
        """Get the persistence backend for this entity instance."""
        return self.__class__._get_config_value("persistence_backend", MemoryRepo())
    
    @property
    def signals(self) -> Dict[str, Any]:
        if self.use_namespace:
            return {self.namespace:self.model_dump()}
        else:
            return self.model_dump()

    # TODO: event decorators are removed 
    async def live(self, heartbeat: float = 15):
        while True:
            yield self.signals
            await asyncio.sleep(heartbeat)

    # TODO: event decorators are removed 
    async def poll(self):
        pass

    # TODO: event decorators are removed
    async def sync(self, datastar):    
        self.set_from_request(datastar)
        return self.signals
    
    def PollDiv(self, heartbeat: float = 0):
        return Div({f"data-on-interval__duration.{heartbeat}s.leading": self.poll()}, id=f"{self.namespace}")

    def PullSyncDiv(self):
        return Div({"data-on-online__window": self.sync(self.signals)}, id=f"{self.namespace}")
    
    def save(self, ttl: Optional[int] = None) -> bool:
        """Save entity to configured backend."""
        return self.persistence_backend.save_entity_sync(self, ttl)
        
    
    def delete(self) -> bool:
        """Delete entity from configured backend."""
        return self.persistence_backend.delete_entity_sync(self.id)
    
    def exists(self) -> bool:
        """Check if entity exists in configured backend."""
        return self.persistence_backend.exists_sync(self.id)
    
    def set_from_request(self, req: Request, **kwargs) -> 'Entity':
        """Initialize entity instance with Datastar payload."""
        # Import here to avoid circular dependency
        from .events import datastar_from_queryParams
        datastar = datastar_from_queryParams(req)    
        for f in self.__class__.model_fields.keys():      
            fns = self.__class__.__name__+"."+f  
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
    def get(cls, req: Request, **kwargs) -> 'Entity':
        """Get cached entity or create new."""
        entity_id = cls._get_id(req, **kwargs)
        
        # Try to get from persistence backend
        persistence_backend = cls._get_config_value("persistence_backend", MemoryRepo())
        cached = persistence_backend.load_entity_sync(entity_id)        
        if cached and isinstance(cached, cls):
            return cached
            
        return cls(req, id=entity_id, **kwargs)
    
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
    def _get_id(cls, req: Request,call_default_factory=True, **kwargs) -> str:
        """Legacy method - use _get_id instead."""
        id = cls.model_fields['id'].get_default(call_default_factory=call_default_factory)
        if id is PydanticUndefined:
            return cls.get_session_id(req, **kwargs)
        return id
    
    def __ft__(self):
        """Render with data-signals attributes."""
        signals = json.dumps(self.signals)
        return Div({"data-signals": signals}, id=f"{self.namespace}")
    
    def __init__(self, req: Request = None, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = self._get_id(req, **kwargs)
        
        # Sync with client FIRST - get latest entity if configured
        self._sync_from_client(req)
        
        # Finally auto-save the synced entity
        if self.auto_persist:
            self.save()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._original_methods = {}
        event_functions = []
        for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(func, '_event_config'):
                cls._original_methods[name] = func
                event_functions.append((name, func))
        
        # Import here to avoid circular dependency
        if event_functions:
            from .events import _register_event_route, _add_url_generator
            for name, func in event_functions:
                _register_event_route(cls, func, func._event_config)
                _add_url_generator(cls, name, func, func._event_config)
        
        if cls._get_config_value("namespace") is None and cls._get_config_value("use_namespace", True):
            cls._set_config_value("namespace", cls.__name__)
    

State = Entity # TODO: remove this
    