"""
Reactive Signal System - Core Reactivity for StarModel

🔄 Automatic UI Synchronization:
This module implements StarModel's reactive signal system that automatically
keeps UI in sync with entity state. Signals provide a clean abstraction
for binding entity data to UI components.

Key Features:
- Automatic signal generation for all entity fields
- Namespace support for complex applications
- Clean separation from web framework specifics
- Datastar integration for real-time updates
- Computed signal support
"""

from typing import Any, Dict, Optional, Type, Union, Callable
from pydantic._internal._model_construction import ModelMetaclass
import weakref

class SignalDescriptor:
    """
    Descriptor that provides reactive signals for entity fields.
    
    When accessed on a class, returns the signal name (e.g., "$field" or "$Entity.field").
    When accessed on an instance, returns the actual field value.
    
    This dual behavior enables both UI binding and direct data access:
    - Class access: MyEntity.name_signal → "$name" (for UI binding)
    - Instance access: my_entity.name_signal → "John" (actual value)
    """
    
    def __init__(self, field_name: str, entity_class: Optional[Type] = None):
        self.field_name = field_name
        self.entity_class = weakref.ref(entity_class) if entity_class else None
    
    def __get__(self, instance, owner):
        # Class access - return signal name for UI binding
        if instance is None:
            return self._get_signal_name(owner)
        
        # Instance access - return actual field value
        return getattr(instance, self.field_name, None)
    
    def __set__(self, instance, value):
        """Allow setting the underlying field value"""
        setattr(instance, self.field_name, value)
        
        # Trigger signal update notifications if configured
        if hasattr(instance, '_notify_signal_change'):
            instance._notify_signal_change(self.field_name, value)
    
    def _get_signal_name(self, owner_class: Type) -> str:
        """Generate the signal name for UI binding"""
        config = getattr(owner_class, "model_config", {})
        
        # Check for namespace configuration
        use_namespace = getattr(config, "use_namespace", False)
        namespace = getattr(config, "namespace", None)
        
        if use_namespace:
            if not namespace:
                namespace = owner_class.__name__
            return f"${namespace}.{self.field_name}"
        else:
            return f"${self.field_name}"
    
    def __repr__(self):
        return f"SignalDescriptor({self.field_name})"

class ComputedSignalDescriptor:
    """
    Descriptor for computed signals that derive from other entity fields.
    
    Computed signals automatically update when their dependencies change.
    """
    
    def __init__(self, field_name: str, compute_func: Callable, dependencies: list = None):
        self.field_name = field_name
        self.compute_func = compute_func
        self.dependencies = dependencies or []
        self._cache = weakref.WeakKeyDictionary()
    
    def __get__(self, instance, owner):
        if instance is None:
            # Class access - return signal name
            config = getattr(owner, "model_config", {})
            use_namespace = getattr(config, "use_namespace", False)
            namespace = getattr(config, "namespace", None)
            
            if use_namespace:
                if not namespace:
                    namespace = owner.__name__
                return f"${namespace}.{self.field_name}"
            else:
                return f"${self.field_name}"
        
        # Instance access - compute and cache value
        if instance not in self._cache:
            self._cache[instance] = self.compute_func(instance)
        
        return self._cache[instance]
    
    def invalidate_cache(self, instance):
        """Invalidate cached value when dependencies change"""
        if instance in self._cache:
            del self._cache[instance]

class SignalRegistry:
    """
    Registry for managing signals across all entities.
    
    Provides centralized management of signal subscriptions,
    change notifications, and dependency tracking.
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, list] = {}
        self._computed_dependencies: Dict[str, list] = {}
    
    def subscribe(self, signal_name: str, callback: Callable):
        """Subscribe to signal changes"""
        if signal_name not in self._subscriptions:
            self._subscriptions[signal_name] = []
        self._subscriptions[signal_name].append(callback)
    
    def unsubscribe(self, signal_name: str, callback: Callable):
        """Unsubscribe from signal changes"""
        if signal_name in self._subscriptions:
            self._subscriptions[signal_name].remove(callback)
    
    def notify_change(self, signal_name: str, new_value: Any, entity_instance=None):
        """Notify all subscribers of a signal change"""
        if signal_name in self._subscriptions:
            for callback in self._subscriptions[signal_name]:
                try:
                    callback(signal_name, new_value, entity_instance)
                except Exception as e:
                    print(f"Signal callback error: {e}")
    
    def register_computed_dependency(self, computed_signal: str, dependency: str):
        """Register a dependency relationship for computed signals"""
        if computed_signal not in self._computed_dependencies:
            self._computed_dependencies[computed_signal] = []
        self._computed_dependencies[computed_signal].append(dependency)
    
    def get_dependents(self, signal_name: str) -> list:
        """Get all computed signals that depend on this signal"""
        dependents = []
        for computed, deps in self._computed_dependencies.items():
            if signal_name in deps:
                dependents.append(computed)
        return dependents

# Global signal registry
_signal_registry = SignalRegistry()

class SignalMixin:
    """
    Mixin that provides signal capabilities to entity classes.
    
    This mixin adds:
    - Signal change notifications
    - Signal value retrieval
    - Integration with the signal registry
    """
    
    def _notify_signal_change(self, field_name: str, new_value: Any):
        """Notify the signal registry of a field change"""
        signal_name = self._get_signal_name(field_name)
        _signal_registry.notify_change(signal_name, new_value, self)
        
        # Also notify any computed signals that depend on this field
        dependents = _signal_registry.get_dependents(signal_name)
        for dependent in dependents:
            # Invalidate computed signal cache
            descriptor = self._get_signal_descriptor(dependent)
            if isinstance(descriptor, ComputedSignalDescriptor):
                descriptor.invalidate_cache(self)
    
    def _get_signal_name(self, field_name: str) -> str:
        """Get the full signal name for a field"""
        config = getattr(self.__class__, "model_config", {})
        use_namespace = getattr(config, "use_namespace", False)
        namespace = getattr(config, "namespace", None)
        
        if use_namespace:
            if not namespace:
                namespace = self.__class__.__name__
            return f"${namespace}.{field_name}"
        else:
            return f"${field_name}"
    
    def _get_signal_descriptor(self, signal_name: str):
        """Get the signal descriptor for a given signal name"""
        # Remove the $ prefix and namespace if present
        clean_name = signal_name.lstrip('$')
        if '.' in clean_name:
            _, field_name = clean_name.split('.', 1)
        else:
            field_name = clean_name
        
        descriptor_name = f"{field_name}_signal"
        return getattr(self.__class__, descriptor_name, None)
    
    def get_all_signals(self) -> Dict[str, Any]:
        """Get all signal values for this entity instance"""
        signals = {}
        
        # Regular fields
        for field_name in self.__class__.model_fields:
            signal_name = self._get_signal_name(field_name)
            signals[signal_name] = getattr(self, field_name)
        
        # Computed fields
        for field_name in getattr(self.__class__, 'model_computed_fields', {}):
            signal_name = self._get_signal_name(field_name)
            try:
                signals[signal_name] = getattr(self, field_name)
            except Exception:
                # Computed field might not be available
                pass
        
        return signals
    
    def get_signal_value(self, field_name: str) -> Any:
        """Get the current value of a specific signal"""
        return getattr(self, field_name)
    
    def set_signal_value(self, field_name: str, value: Any):
        """Set a signal value and trigger notifications"""
        old_value = getattr(self, field_name, None)
        setattr(self, field_name, value)
        
        if old_value != value:
            self._notify_signal_change(field_name, value)

class SignalModelMeta(ModelMetaclass):
    """
    Metaclass that automatically creates signal descriptors for all entity fields.
    
    This metaclass:
    1. Creates signal descriptors for all model fields
    2. Sets up computed signal dependencies
    3. Configures namespace settings
    4. Integrates with the event system
    """
    
    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace, **kwargs)
        
        # Create signal descriptors for all declared fields
        cls._setup_field_signals()
        
        # Create signal descriptors for computed fields
        cls._setup_computed_signals()
        
        # Set up event method descriptors (if events are present)
        cls._setup_event_descriptors()
    
    def _setup_field_signals(cls):
        """Create signal descriptors for all model fields"""
        for field_name in cls.model_fields:
            signal_descriptor = SignalDescriptor(field_name, cls)
            setattr(cls, f"{field_name}_signal", signal_descriptor)
    
    def _setup_computed_signals(cls):
        """Create signal descriptors for computed fields"""
        for field_name in getattr(cls, 'model_computed_fields', {}):
            signal_descriptor = SignalDescriptor(field_name, cls)
            setattr(cls, f"{field_name}_signal", signal_descriptor)
    
    def _setup_event_descriptors(cls):
        """Set up event method descriptors for URL generation"""
        # Import here to avoid circular imports
        try:
            from ...events.commands.event import EventMethodDescriptor
            
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name)
                if hasattr(attr, '_event_metadata'):
                    # Create URL generator method
                    url_generator = EventMethodDescriptor(attr_name, cls.__name__, attr)
                    setattr(cls, attr_name, url_generator)
        except ImportError:
            # During migration, use the old import
            try:
                from starmodel.core.signals import EventMethodDescriptor
                
                for attr_name in dir(cls):
                    attr = getattr(cls, attr_name)
                    if hasattr(attr, '_event_info'):
                        # Create URL generator method
                        url_generator = EventMethodDescriptor(attr_name, cls.__name__, attr)
                        setattr(cls, attr_name, url_generator)
            except ImportError:
                # Skip event setup during early migration
                pass

# Utility functions for signal management
def reactive_signal(func):
    """
    Decorator to create a computed signal from a method.
    
    The decorated method becomes a computed property that
    automatically updates when its dependencies change.
    """
    def wrapper(self):
        return func(self)
    
    # Mark as computed signal
    wrapper._is_computed_signal = True
    wrapper._compute_func = func
    
    return property(wrapper)

def watch_signal(signal_name: str, callback: Callable):
    """
    Watch a signal for changes.
    
    Args:
        signal_name: The signal to watch (e.g., "User.name" or "count")
        callback: Function to call when signal changes
    """
    _signal_registry.subscribe(signal_name, callback)

def unwatch_signal(signal_name: str, callback: Callable):
    """Stop watching a signal for changes"""
    _signal_registry.unsubscribe(signal_name, callback)

def get_signal_registry() -> SignalRegistry:
    """Get the global signal registry"""
    return _signal_registry

# Datastar integration utilities
def signals_to_datastar_format(signals: Dict[str, Any]) -> str:
    """
    Convert signal dictionary to Datastar-compatible format.
    
    This will be moved to the Datastar adapter once web integration is migrated.
    """
    import json
    
    # Convert signal names to Datastar format
    datastar_data = {}
    for signal_name, value in signals.items():
        # Remove $ prefix for Datastar
        clean_name = signal_name.lstrip('$')
        datastar_data[clean_name] = value
    
    return json.dumps(datastar_data)

def merge_signals(*signal_dicts: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple signal dictionaries"""
    merged = {}
    for signal_dict in signal_dicts:
        merged.update(signal_dict)
    return merged

# Export main components
__all__ = [
    "SignalDescriptor", "ComputedSignalDescriptor", "SignalMixin", 
    "SignalModelMeta", "SignalRegistry", "reactive_signal",
    "watch_signal", "unwatch_signal", "get_signal_registry",
    "signals_to_datastar_format", "merge_signals"
]