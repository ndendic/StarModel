from typing import Any, Optional
from datetime import datetime

from fastcore.xml import *
from starlette.requests import Request
from pydantic import BaseModel, Field, ConfigDict
from ..persistence import MemoryRepo, EntityPersistenceBackend
from .signals import SignalDescriptor, EventMethodDescriptor
from .events import event
from .mixins import EntityMixin, PersistenceMixin

datastar_script = Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0-beta.11/bundles/datastar.js", type="module")

class EntityConfig(ConfigDict):
    """Configuration for all entity classes."""
    namespace: str | None
    use_namespace: bool
    auto_persist: bool
    persistence_backend: EntityPersistenceBackend
    sync_with_client: bool
    ttl: Optional[int]

class Entity(EntityMixin, PersistenceMixin, BaseModel):
    """Base class for all entity classes."""
    model_config = EntityConfig(arbitrary_types_allowed=True,
                                use_namespace=True,
                                auto_persist=True,
                                persistence_backend=MemoryRepo(),
                                sync_with_client=True,
                                json_encoders={datetime: lambda dt: dt.isoformat()})

    id: str = Field(primary_key=True)

    # All core functionality now provided by mixins
    # EntityMixin provides: configuration, signals, event handling
    # PersistenceMixin provides: save, delete, exists methods
    
    @event
    async def live(self, heartbeat: float = 15):
        """Live event for real-time updates."""
        return await super().live(heartbeat)

    @event
    async def poll(self):
        """Poll event for periodic updates."""
        return await super().poll()

    @event
    async def sync(self, datastar):    
        """Sync event for client synchronization."""
        return await super().sync(datastar)
    
    def __init__(self, req: Request = None, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = self._get_id(req, **kwargs)
        
        # Sync with client FIRST - get latest entity if configured
        self._sync_from_client(req)
        
        # Finally auto-save the synced entity
        if self.auto_persist:
            self.save()

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        
        # Create signal descriptors for all model fields
        for field_name in cls.model_fields:
            setattr(cls, f"S{field_name}", SignalDescriptor(field_name))
        for field_name in cls.model_computed_fields:
            setattr(cls, f"S{field_name}", SignalDescriptor(field_name))
        
        # Create URL generator methods for @event decorated methods
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_event_info'):
                # Create URL generator method that overrides the original method on the class
                event_descriptor = EventMethodDescriptor(attr_name, cls.__name__, attr)
                setattr(cls, attr_name, event_descriptor)
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        if cls._namespace is None and cls._use_namespace:
            cls._namespace = cls.__name__
    

State = Entity # TODO: remove this
    