import inspect
import asyncio
import json
from typing import Any, Dict, Optional

from fasthtml.common import *
from pydantic import BaseModel, Field
from pydantic_core import PydanticUndefined

from .persistence import memory_persistence, StateStore
from .event import _register_event_route, _add_url_generator, event, datastar_from_queryParams
from .signals import SignalModelMeta

datastar_script = Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0-beta.11/bundles/datastar.js", type="module")

class State(BaseModel, metaclass=SignalModelMeta):
    """Base class for all state classes."""
    model_config = {
        "arbitrary_types_allowed": True,
        "namespace": None, # will set to class name if None
        "use_namespace": True, # whether to use namespaced signals
        "store": StateStore.SERVER_MEMORY,
        "auto_persist": True,
        "persistence_backend": memory_persistence,
        "sync_with_client": True,
    }

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
        """Get the namespace for this state instance."""
        return self.__class__._get_config_value("namespace", None)
    
    @property
    def use_namespace(self):
        """Get the use_namespace setting for this state instance."""
        return self.__class__._get_config_value("use_namespace", True)

    @property
    def store(self):
        """Get the store for this state instance."""
        return self.__class__._get_config_value("store", StateStore.SERVER_MEMORY)
    
    @property
    def sync_with_client(self):
        """Get the sync_with_client setting for this state instance."""
        return self.__class__._get_config_value("sync_with_client", True)
    
    @property
    def auto_persist(self):
        """Get the auto_persist setting for this state instance."""
        return self.__class__._get_config_value("auto_persist", True)
    
    @property
    def persistence_backend(self):
        """Get the persistence backend for this state instance."""
        return self.__class__._get_config_value("persistence_backend", memory_persistence)
    
    @property
    def signals(self) -> Dict[str, Any]:
        if self.use_namespace:
            return {self.namespace:self.model_dump()}
        else:
            return self.model_dump()

    @event
    async def live(self, heartbeat: float = 15):
        while True:
            yield self.signals
            await asyncio.sleep(heartbeat)

    @event
    async def poll(self):
        pass

    @event
    async def sync(self, datastar):    
        self.set_from_request(datastar)
        return self.signals
    
    def PollDiv(self, heartbeat: float = 0):
        return Div({f"data-on-interval__duration.{heartbeat}s.leading": self.poll()}, id=f"{self.namespace}")

    def PullSyncDiv(self):
        return Div({"data-on-online__window": self.sync(self.signals)}, id=f"{self.namespace}")
    
    def save(self, ttl: Optional[int] = None) -> bool:
        """Save state to configured backend."""
        if self.store.startswith("client_"):
            return True  # Datastar handles client persistence        
        # Save using configured persistence backend
        return self.persistence_backend.save_state_sync(self, ttl)
    
    def _sync_from_client(self, req: Request):
        """Sync state with client-side changes using datastar payload."""
        if req and self.sync_with_client:
            self.set_from_request(req)
    
    def delete(self) -> bool:
        """Delete state from configured backend."""
        if self.store.startswith("client_"):
            return True  # Cannot delete client storage from server
            
        return self.persistence_backend.delete_state_sync(self.id)
    
    def exists(self) -> bool:
        """Check if state exists in configured backend."""
        if self.store.startswith("client_"):
            return False  # Cannot check client storage from server
            
        return self.persistence_backend.exists_sync(self.id)
    
    def set_from_request(self, req: Request, **kwargs) -> 'State':
        """Initialize state instance with Datastar payload."""    
        datastar = datastar_from_queryParams(req)    
        for f in self.__class__.model_fields.keys():      
            fns = self.__class__.__name__+"."+f  
            if f in datastar:
                setattr(self, f, datastar[f])
            elif fns in datastar:
                setattr(self, f, datastar[fns])
        return self

    @classmethod
    def get(cls, req: Request, **kwargs) -> 'State':
        """Get cached state or create new."""
        state_id = cls._get_id(req, **kwargs)
        cached = memory_persistence._data.get(state_id)        
        if cached and isinstance(cached, cls):
            return cached
        return cls(req, id=state_id, **kwargs)
    
    @classmethod
    def get_session_id(cls, req: Request, **kwargs) -> str:
        """Generate deterministic state ID. Override in subclasses for custom logic."""
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
        """Render with appropriate data-persist attributes for client-side stores."""
        signals = json.dumps(self.signals)
        
        if self.store == StateStore.CLIENT_SESSION:
            return Div({"data-signals": signals,
                        "data-on-online__window": self.sync(),
                        "data-on-load": self.sync(),
                        "data-persist__session": True},
                        id=f"{self.namespace}")
        elif self.store == StateStore.CLIENT_LOCAL:
            return Div({"data-signals": signals,
                        "data-on-online__window": self.sync(),
                        "data-on-load": self.sync(),
                        "data-persist": True},
                        id=f"{self.namespace}")
        else:
            return Div({"data-signals": signals}, id=f"{self.namespace}")
    
    def __init__(self, req: Request = None, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = self._get_id(req, **kwargs)
        
        # Sync with client FIRST - get latest state
        self._sync_from_client(req)
        
        # Finally auto-save the synced state
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
        
        for name, func in event_functions:
            _register_event_route(cls, func, func._event_config)
            _add_url_generator(cls, name, func, func._event_config)
        
        if cls._get_config_value("namespace") is None and cls._get_config_value("use_namespace", True):
            cls._set_config_value("namespace", cls.__name__)
    
    