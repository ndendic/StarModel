"""
Signal Service - Reactive Signal Management

🔄 Reactive UI Binding:
This service handles reactive signals for entities, providing clean separation
between business logic and UI concerns through dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Callable, TYPE_CHECKING
import inspect

if TYPE_CHECKING:
    from ..lifecycle.entity import Entity


class SignalService(ABC):
    """
    Abstract interface for managing reactive signals.
    
    This service is injected into entities to handle signal generation,
    updates, and UI binding without coupling entities to UI frameworks.
    """
    
    @abstractmethod
    def get_field_signals(self, entity: 'Entity') -> Dict[str, str]:
        """Get all field signals for an entity"""
        pass
    
    @abstractmethod
    def get_signal_key(self, entity: 'Entity', field_name: str) -> str:
        """Get the signal key for a specific field"""
        pass
    
    @abstractmethod
    def get_signals_update(self, entity: 'Entity', changed_fields: List[str] = None) -> Dict[str, Any]:
        """Get signal updates for changed fields"""
        pass
    
    @abstractmethod
    def create_signal_descriptor(self, field_name: str, entity_class: Type['Entity']) -> Any:
        """Create a signal descriptor for a field"""
        pass
    
    @abstractmethod
    def setup_entity_signals(self, entity_class: Type['Entity']):
        """Set up signals for an entity class"""
        pass


class ReactiveSignalService(SignalService):
    """
    Default implementation of signal service with reactive capabilities.
    
    This service generates Datastar-compatible signals and handles
    UI binding for real-time updates.
    """
    
    def __init__(self, use_namespace: bool = False, namespace_prefix: str = ""):
        self.use_namespace = use_namespace
        self.namespace_prefix = namespace_prefix
        self._signal_descriptors: Dict[str, Any] = {}
    
    def get_field_signals(self, entity: 'Entity') -> Dict[str, str]:
        """Get all field signals for an entity"""
        signals = {}
        
        # Get model fields
        if hasattr(entity.__class__, 'model_fields'):
            for field_name in entity.__class__.model_fields:
                signal_key = self.get_signal_key(entity, field_name)
                signals[signal_key] = getattr(entity, field_name, None)
        
        # Get computed fields if available
        if hasattr(entity.__class__, 'model_computed_fields'):
            for field_name in entity.__class__.model_computed_fields:
                try:
                    signal_key = self.get_signal_key(entity, field_name)
                    signals[signal_key] = getattr(entity, field_name, None)
                except Exception:
                    # Computed field might not be available
                    pass
        
        return signals
    
    def get_signal_key(self, entity: 'Entity', field_name: str) -> str:
        """Get the signal key for a specific field"""
        if self.use_namespace:
            namespace = self.namespace_prefix or entity.__class__.__name__
            return f"{namespace}.{field_name}"
        return field_name
    
    def get_signals_update(self, entity: 'Entity', changed_fields: List[str] = None) -> Dict[str, Any]:
        """Get signal updates for changed fields"""
        if changed_fields is None:
            # Return all signals if no specific fields specified
            return self.get_field_signals(entity)
        
        signals = {}
        for field_name in changed_fields:
            if hasattr(entity, field_name):
                signal_key = self.get_signal_key(entity, field_name)
                signals[signal_key] = getattr(entity, field_name)
        
        return signals
    
    def create_signal_descriptor(self, field_name: str, entity_class: Type['Entity']) -> Any:
        """Create a signal descriptor for a field"""
        
        class SignalDescriptor:
            """Descriptor that generates signal keys for Datastar binding"""
            
            def __init__(self, field_name: str, entity_class: Type, signal_service: SignalService):
                self.field_name = field_name
                self.entity_class = entity_class
                self.signal_service = signal_service
            
            def __get__(self, instance, owner):
                if instance is not None:
                    # Return actual field value when accessed on instance
                    return getattr(instance, self.field_name, None)
                else:
                    # Return signal key when accessed on class (for Datastar attributes)
                    dummy_entity = owner()  # Create temporary instance to get signal key
                    signal_key = self.signal_service.get_signal_key(dummy_entity, self.field_name)
                    return f"${signal_key}"
            
            def __set__(self, instance, value):
                # Set the actual field value
                setattr(instance, f"_{self.field_name}", value)
        
        return SignalDescriptor(field_name, entity_class, self)
    
    def setup_entity_signals(self, entity_class: Type['Entity']):
        """Set up signals for an entity class"""
        # Create signal descriptors for all model fields
        if hasattr(entity_class, 'model_fields'):
            for field_name in entity_class.model_fields:
                signal_name = f"{field_name}_signal"
                descriptor = self.create_signal_descriptor(field_name, entity_class)
                setattr(entity_class, signal_name, descriptor)
        
        # Create signal descriptors for computed fields
        if hasattr(entity_class, 'model_computed_fields'):
            for field_name in entity_class.model_computed_fields:
                signal_name = f"{field_name}_signal"
                descriptor = self.create_signal_descriptor(field_name, entity_class)
                setattr(entity_class, signal_name, descriptor)


class SimpleSignalService(SignalService):
    """
    Simple signal service for testing and minimal deployments.
    
    This implementation provides basic signal functionality without
    external dependencies or complex UI framework integration.
    """
    
    def get_field_signals(self, entity: 'Entity') -> Dict[str, str]:
        """Get simple field-value mapping"""
        signals = {}
        
        # Use model_dump if available (Pydantic), otherwise use __dict__
        if hasattr(entity, 'model_dump'):
            data = entity.model_dump()
        else:
            data = {k: v for k, v in entity.__dict__.items() if not k.startswith('_')}
        
        return data
    
    def get_signal_key(self, entity: 'Entity', field_name: str) -> str:
        """Return simple field name as signal key"""
        return field_name
    
    def get_signals_update(self, entity: 'Entity', changed_fields: List[str] = None) -> Dict[str, Any]:
        """Get updates for changed fields"""
        all_signals = self.get_field_signals(entity)
        
        if changed_fields is None:
            return all_signals
        
        return {field: all_signals.get(field) for field in changed_fields if field in all_signals}
    
    def create_signal_descriptor(self, field_name: str, entity_class: Type['Entity']) -> Any:
        """Create simple signal descriptor"""
        
        class SimpleSignalDescriptor:
            """Simple descriptor that returns field name as signal"""
            
            def __init__(self, field_name: str):
                self.field_name = field_name
            
            def __get__(self, instance, owner):
                if instance is not None:
                    return getattr(instance, self.field_name, None)
                else:
                    return f"${self.field_name}"
        
        return SimpleSignalDescriptor(field_name)
    
    def setup_entity_signals(self, entity_class: Type['Entity']):
        """Set up simple signals for entity class"""
        # For simple implementation, we just store the service reference
        # Actual signal access happens through the service methods
        entity_class._signal_service = self


# Export main components
__all__ = [
    "SignalService", "ReactiveSignalService", "SimpleSignalService"
]