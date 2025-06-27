from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sqlmodel import SQLModel, Field
# from fasthtml.common import *
from pydantic import ConfigDict

from .mixins import EntityMixin, PersistenceMixin
from .signals import SignalDescriptor, EventMethodDescriptor
from ..persistence import SQLModelBackend
from .events import event

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SQLEntity(EntityMixin, PersistenceMixin, SQLModel):
    # SQLAlchemy table configuration
    __table_args__ = {'extend_existing': True}

    # Pydantic model configuration (for validation/serialization)
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        validate_assignment=True,
        json_encoders={datetime: lambda dt: dt.isoformat()}
    )
    
    # Override persistence backend class for SQL entities
    _persistence_backend_class = SQLModelBackend
    
    # Define id field for SQLModel
    id: str = Field(primary_key=True)

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
                # Create URL generator method that overrides the original method on the class
                url_generator = EventMethodDescriptor(attr_name, cls.__name__, attr)
                setattr(cls, attr_name, url_generator)
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        if cls._namespace is None and cls._use_namespace:
            cls._namespace = cls.__name__
            
        # Ensure SQLEntity subclasses use SQLModelBackend
        cls._persistence_backend_class = SQLModelBackend

    @classmethod
    def related_records(cls) -> dict[str, List]:
        pass

    @classmethod
    def all(cls) -> List["SQLEntity"]:
        backend = cls._persistence_backend_class()
        return backend.all_records(cls)

    @classmethod
    def total_records(cls) -> int:
        return len(cls.all())

    @classmethod
    def search(
        cls,
        search_value: Optional[str] = None,
        sorting_field: Optional[str] = None,
        sort_direction: str = "asc",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        as_dict: bool = False,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        backend = cls._persistence_backend_class()
        return backend.search(
            cls,
            search_value=search_value,
            sorting_field=sorting_field,
            sort_direction=sort_direction,
            limit=limit,
            offset=offset,
            as_dict=as_dict,
            fields=fields,
        )

    @classmethod
    def filter(cls,
        sorting_field: Optional[str] = None,
        sort_direction: str = "asc",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        as_dict: bool = False,
        fields: Optional[List[str]] = None,
        exact_match: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        backend = cls._persistence_backend_class()
        return backend.filter(
            model=cls,
            sorting_field=sorting_field,
            sort_direction=sort_direction,
            limit=limit,
            offset=offset,
            as_dict=as_dict,
            fields=fields,
            exact_match=exact_match,
            **kwargs
        )

    @classmethod
    def table_view_data(cls, request) -> List[Dict[str, Any]]:
        search_value = None
        page = 1
        per_page = 10
        view_fields = cls.table_view_fields

        if "id" not in view_fields:
            view_fields.append("id")

        if hasattr(request, "query_params"):
            search_value = request.query_params.get("search_value")
            page = int(request.query_params.get("page", 1))
            per_page = int(request.query_params.get("per_page", 10))

        offset = (page - 1) * per_page

        records = cls.search(
            search_value=search_value,
            sorting_field=cls.default_sort_field,
            sort_direction="asc",
            limit=per_page,
            offset=offset,
            as_dict=True,
            fields=view_fields,
        )
        return records

    @classmethod
    def get(cls, req, id: Any = None, alt_key: str = None, **kwargs) -> 'SQLEntity':
        """Get cached entity or create new - SQL version."""
        if id is None:
            entity_id = cls._get_id(req, **kwargs)
        else:
            entity_id = id
        
        # Try to get from persistence backend
        backend = cls._persistence_backend_class()
        cached = backend.load_entity_sync(cls, entity_id, alt_key)        
        if cached and isinstance(cached, cls):
            return cached
        
        return cls(id=entity_id, **kwargs)
        
    
    @classmethod
    def update_record(cls, id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        backend = cls._persistence_backend_class()
        return backend.update_record(cls, id, data)

    @classmethod
    def delete_record(cls, id: Any) -> None:
        backend = cls._persistence_backend_class()
        return backend.delete_record(cls, id)

    @classmethod
    def upsert(cls, data: Dict[str, Any]) -> "SQLEntity":
        backend = cls._persistence_backend_class()
        return backend.upsert_record(cls, data)

    @classmethod
    def _cast_data(cls, data: List[Dict[str, Any]]) -> List["SQLEntity"]:
        return [cls(**item) for item in data]

    def exists(self) -> bool:
        db = self.persistence_backend
        if db.load_entity_sync(type(self), self.id):
            return True
        return False

    # Override save method to return SQLEntity instead of bool
    def save(self, ttl: Optional[int] = None) -> "SQLEntity":
        db = self.persistence_backend
        return db.save_entity_sync(self, ttl)
    
    # Override delete method
    def delete(self) -> None:
        db = self.persistence_backend
        db.delete_entity_sync(self)
    
    # Add event methods
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
    
    def dict(self, *args, **kwargs):
        return self._dict_with_custom_encoder(set(), *args, **kwargs)

    def _dict_with_custom_encoder(self, processed: Set[int], *args, **kwargs):
        if id(self) in processed:
            return {"id": getattr(self, "id", None)}

        processed.add(id(self))

        data = {}
        for field in self.model_fields:
            value = getattr(self, field)
            if isinstance(value, SQLEntity):
                value = value._dict_with_custom_encoder(processed, *args, **kwargs)
            elif isinstance(value, list):
                value = [
                    item._dict_with_custom_encoder(processed, *args, **kwargs)
                    if isinstance(item, SQLEntity)
                    else item
                    for item in value
                ]
            elif isinstance(value, dict):
                value = {
                    k: v._dict_with_custom_encoder(processed, *args, **kwargs)
                    if isinstance(v, SQLEntity)
                    else v
                    for k, v in value.items()
                }
            elif isinstance(value, datetime):
                value = value.isoformat()

            data[field] = value

        return data