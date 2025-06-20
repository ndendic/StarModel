"""
Composition-Based Entity - Dependency Injection over Inheritance

🏗️ Clean Architecture Entity:
This entity implementation uses composition over inheritance, injecting services
for persistence, validation, events, signals, and metrics rather than mixing them in.
"""

from typing import Any, Dict, List, Optional, Type, ClassVar
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

try:
    from ..services.persistence_service import PersistenceService, InMemoryPersistenceService
    from ..services.validation_service import ValidationService, SimpleValidationService
    from ..services.event_service import EventService, SimpleEventService
    from ..services.signal_service import SignalService, SimpleSignalService
    from ..services.metrics_service import MetricsService, SimpleMetricsService
except ImportError:
    # Fallback imports for standalone testing
    from typing import Protocol
    
    class PersistenceService(Protocol):
        def generate_id(self) -> str: ...
        async def save(self, entity, **kwargs) -> str: ...
        async def load(self, entity_class, entity_id: str): ...
        async def delete(self, entity_class, entity_id: str) -> bool: ...
        async def exists(self, entity_class, entity_id: str) -> bool: ...
        async def list_all(self, entity_class, limit: int = 100): ...
    
    class ValidationService(Protocol):
        def validate_entity(self, entity) -> bool: ...
        def validate_field(self, entity, field_name: str, value) -> bool: ...
        def get_validation_errors(self, entity) -> Dict[str, List[str]]: ...
        def setup_entity_validation(self, entity_class): ...
    
    class EventService(Protocol):
        async def execute_event(self, entity, event_name: str, parameters: Dict[str, Any]): ...
        def get_entity_events(self, entity_class): ...
        def has_event(self, entity_class, event_name: str) -> bool: ...
        def setup_entity_events(self, entity_class): ...
    
    class SignalService(Protocol):
        def get_field_signals(self, entity) -> Dict[str, str]: ...
        def get_signal_key(self, entity, field_name: str) -> str: ...
        def get_signals_update(self, entity, changed_fields: List[str] = None) -> Dict[str, Any]: ...
        def setup_entity_signals(self, entity_class): ...
    
    class MetricsService(Protocol):
        def record_operation(self, entity, operation: str, duration_ms: float = None): ...
        def record_event_execution(self, entity, event_name: str, duration_ms: float, success: bool): ...
        def record_persistence_operation(self, entity_class, operation: str, duration_ms: float): ...
        def get_entity_metrics(self, entity) -> Dict[str, Any]: ...
        def get_class_metrics(self, entity_class) -> Dict[str, Any]: ...
    
    # Simple implementations for standalone testing
    class InMemoryPersistenceService:
        def __init__(self):
            self._storage = {}
        
        def generate_id(self) -> str:
            return str(uuid.uuid4())
        
        async def save(self, entity, **kwargs) -> str:
            if not entity.id:
                entity.id = self.generate_id()
            self._storage[entity.id] = entity
            return entity.id
        
        async def load(self, entity_class, entity_id: str):
            return self._storage.get(entity_id)
        
        async def delete(self, entity_class, entity_id: str) -> bool:
            if entity_id in self._storage:
                del self._storage[entity_id]
                return True
            return False
        
        async def exists(self, entity_class, entity_id: str) -> bool:
            return entity_id in self._storage
        
        async def list_all(self, entity_class, limit: int = 100):
            return list(self._storage.values())[:limit]
    
    class SimpleValidationService:
        def validate_entity(self, entity) -> bool:
            return True
        
        def validate_field(self, entity, field_name: str, value) -> bool:
            return True
        
        def get_validation_errors(self, entity) -> Dict[str, List[str]]:
            return {}
        
        def setup_entity_validation(self, entity_class):
            pass
    
    class SimpleEventService:
        async def execute_event(self, entity, event_name: str, parameters: Dict[str, Any]):
            if hasattr(entity, event_name):
                method = getattr(entity, event_name)
                return method(**parameters)
            return None
        
        def get_entity_events(self, entity_class):
            return {}
        
        def has_event(self, entity_class, event_name: str) -> bool:
            return hasattr(entity_class, event_name)
        
        def setup_entity_events(self, entity_class):
            pass
    
    class SimpleSignalService:
        def get_field_signals(self, entity) -> Dict[str, str]:
            return {k: v for k, v in entity.__dict__.items() if not k.startswith('_')}
        
        def get_signal_key(self, entity, field_name: str) -> str:
            return field_name
        
        def get_signals_update(self, entity, changed_fields: List[str] = None) -> Dict[str, Any]:
            return self.get_field_signals(entity)
        
        def setup_entity_signals(self, entity_class):
            pass
    
    class SimpleMetricsService:
        def record_operation(self, entity, operation: str, duration_ms: float = None):
            pass
        
        def record_event_execution(self, entity, event_name: str, duration_ms: float, success: bool):
            pass
        
        def record_persistence_operation(self, entity_class, operation: str, duration_ms: float):
            pass
        
        def get_entity_metrics(self, entity) -> Dict[str, Any]:
            return {}
        
        def get_class_metrics(self, entity_class) -> Dict[str, Any]:
            return {}


class ServiceContainer:
    """
    Service container for dependency injection.
    
    This container holds all the services that entities need,
    allowing for easy configuration and testing.
    """
    
    def __init__(self):
        # Default services for basic functionality
        self.persistence_service: PersistenceService = InMemoryPersistenceService()
        self.validation_service: ValidationService = SimpleValidationService()
        self.event_service: EventService = SimpleEventService()
        self.signal_service: SignalService = SimpleSignalService()
        self.metrics_service: MetricsService = SimpleMetricsService()
    
    def configure_persistence(self, service: PersistenceService):
        """Configure the persistence service"""
        self.persistence_service = service
        return self
    
    def configure_validation(self, service: ValidationService):
        """Configure the validation service"""
        self.validation_service = service
        return self
    
    def configure_events(self, service: EventService):
        """Configure the event service"""
        self.event_service = service
        return self
    
    def configure_signals(self, service: SignalService):
        """Configure the signal service"""
        self.signal_service = service
        return self
    
    def configure_metrics(self, service: MetricsService):
        """Configure the metrics service"""
        self.metrics_service = service
        return self


# Global service container - can be overridden for testing
_global_container = ServiceContainer()


def get_service_container() -> ServiceContainer:
    """Get the global service container"""
    return _global_container


def set_service_container(container: ServiceContainer):
    """Set the global service container"""
    global _global_container
    _global_container = container


class Entity(BaseModel):
    """
    Composition-based Entity using dependency injection.
    
    This entity gets its capabilities through injected services rather than
    inheritance, providing better testability and separation of concerns.
    """
    
    # Core entity fields
    id: Optional[str] = Field(default=None, description="Unique entity identifier")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Service container for dependency injection
    _services: ClassVar[ServiceContainer] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Initialize entity with services
        if not self.id:
            self.id = self._get_persistence_service().generate_id()
        
        if not self.created_at:
            self.created_at = datetime.now()
        
        if not self.updated_at:
            self.updated_at = self.created_at
        
        # Set up entity-specific services
        self._setup_entity()
    
    @classmethod
    def _get_services(cls) -> ServiceContainer:
        """Get service container for this entity class"""
        if cls._services is None:
            cls._services = get_service_container()
        return cls._services
    
    @classmethod
    def set_services(cls, container: ServiceContainer):
        """Set service container for this entity class"""
        cls._services = container
    
    def _get_persistence_service(self) -> PersistenceService:
        """Get persistence service"""
        return self._get_services().persistence_service
    
    def _get_validation_service(self) -> ValidationService:
        """Get validation service"""
        return self._get_services().validation_service
    
    def _get_event_service(self) -> EventService:
        """Get event service"""
        return self._get_services().event_service
    
    def _get_signal_service(self) -> SignalService:
        """Get signal service"""
        return self._get_services().signal_service
    
    def _get_metrics_service(self) -> MetricsService:
        """Get metrics service"""
        return self._get_services().metrics_service
    
    def _setup_entity(self):
        """Set up entity-specific services"""
        # Set up event methods
        self._get_event_service().setup_entity_events(self.__class__)
        
        # Set up reactive signals
        self._get_signal_service().setup_entity_signals(self.__class__)
        
        # Set up validation
        self._get_validation_service().setup_entity_validation(self.__class__)
        
        # Record entity creation
        self._get_metrics_service().record_operation(self, "create")
    
    # Persistence Operations (delegated to persistence service)
    
    async def save(self, **kwargs) -> str:
        """Save this entity"""
        start_time = datetime.now()
        
        try:
            # Validate before saving
            self.validate()
            
            # Save through persistence service
            entity_id = await self._get_persistence_service().save(self, **kwargs)
            
            # Record metrics
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._get_metrics_service().record_operation(self, "save", duration)
            
            return entity_id
            
        except Exception as e:
            # Record error
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._get_metrics_service().record_operation(self, "save_error", duration)
            raise
    
    @classmethod
    async def load(cls, entity_id: str) -> Optional['Entity']:
        """Load an entity by ID"""
        start_time = datetime.now()
        
        try:
            # Create temporary instance to get services
            temp_instance = cls()
            persistence_service = temp_instance._get_persistence_service()
            metrics_service = temp_instance._get_metrics_service()
            
            # Load through persistence service
            entity = await persistence_service.load(cls, entity_id)
            
            # Record metrics
            duration = (datetime.now() - start_time).total_seconds() * 1000
            metrics_service.record_persistence_operation(cls, "load", duration)
            
            return entity
            
        except Exception as e:
            # Record error
            duration = (datetime.now() - start_time).total_seconds() * 1000
            temp_instance._get_metrics_service().record_persistence_operation(cls, "load_error", duration)
            raise
    
    async def delete(self) -> bool:
        """Delete this entity"""
        if not self.id:
            return False
        
        start_time = datetime.now()
        
        try:
            # Delete through persistence service
            success = await self._get_persistence_service().delete(self.__class__, self.id)
            
            # Record metrics
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._get_metrics_service().record_operation(self, "delete", duration)
            
            return success
            
        except Exception as e:
            # Record error
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._get_metrics_service().record_operation(self, "delete_error", duration)
            raise
    
    async def exists(self) -> bool:
        """Check if this entity exists"""
        if not self.id:
            return False
        
        return await self._get_persistence_service().exists(self.__class__, self.id)
    
    @classmethod
    async def list_all(cls, limit: int = 100) -> List['Entity']:
        """List all entities of this type"""
        # Create temporary instance to get services
        temp_instance = cls()
        persistence_service = temp_instance._get_persistence_service()
        
        return await persistence_service.list_all(cls, limit)
    
    # Validation Operations (delegated to validation service)
    
    def validate(self) -> bool:
        """Validate this entity"""
        return self._get_validation_service().validate_entity(self)
    
    def validate_field(self, field_name: str, value: Any) -> bool:
        """Validate a specific field"""
        return self._get_validation_service().validate_field(self, field_name, value)
    
    def get_validation_errors(self) -> Dict[str, List[str]]:
        """Get all validation errors"""
        return self._get_validation_service().get_validation_errors(self)
    
    # Signal Operations (delegated to signal service)
    
    def signal(self, field_name: str) -> str:
        """Get signal key for a field"""
        return self._get_signal_service().get_signal_key(self, field_name)
    
    def get_signals(self) -> Dict[str, Any]:
        """Get all signals for this entity"""
        return self._get_signal_service().get_field_signals(self)
    
    def get_signal_updates(self, changed_fields: List[str] = None) -> Dict[str, Any]:
        """Get signal updates for changed fields"""
        return self._get_signal_service().get_signals_update(self, changed_fields)
    
    # Event Operations (delegated to event service)
    
    async def execute_event(self, event_name: str, parameters: Dict[str, Any] = None) -> Any:
        """Execute an event method"""
        parameters = parameters or {}
        
        start_time = datetime.now()
        success = True
        
        try:
            # Execute event through event service
            result = await self._get_event_service().execute_event(self, event_name, parameters)
            
            return result
            
        except Exception as e:
            success = False
            raise
            
        finally:
            # Record metrics
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._get_metrics_service().record_event_execution(self, event_name, duration, success)
    
    @classmethod
    def get_events(cls) -> Dict[str, Any]:
        """Get all events for this entity class"""
        # Create temporary instance to get services
        temp_instance = cls()
        return temp_instance._get_event_service().get_entity_events(cls)
    
    @classmethod
    def has_event(cls, event_name: str) -> bool:
        """Check if entity has a specific event"""
        # Create temporary instance to get services
        temp_instance = cls()
        return temp_instance._get_event_service().has_event(cls, event_name)
    
    # Metrics Operations (delegated to metrics service)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics for this entity"""
        return self._get_metrics_service().get_entity_metrics(self)
    
    @classmethod
    def get_class_metrics(cls) -> Dict[str, Any]:
        """Get metrics for this entity class"""
        # Create temporary instance to get services
        temp_instance = cls()
        return temp_instance._get_metrics_service().get_class_metrics(cls)
    
    # Utility Methods
    
    def __setattr__(self, name: str, value: Any):
        """Track field changes for reactive updates"""
        if hasattr(self, '_initialized') and hasattr(self, name):
            # Field is being updated, record for signals
            old_value = getattr(self, name, None)
            if old_value != value:
                self.updated_at = datetime.now()
        
        super().__setattr__(name, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary"""
        if hasattr(self, 'model_dump'):
            return self.model_dump()
        else:
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def __repr__(self) -> str:
        """String representation"""
        return f"{self.__class__.__name__}(id={self.id})"


# Export main components
__all__ = [
    "Entity", "ServiceContainer", "get_service_container", "set_service_container"
]