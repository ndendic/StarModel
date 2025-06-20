"""
Event Capable Mixin - Entity Event Handling

🎯 Clean Architecture Event Capabilities:
This mixin provides event handling capabilities for entities, integrating
with the event dispatcher and command system.
"""

from typing import Dict, Any, List, Optional, ClassVar, Callable
from dataclasses import dataclass, field
import inspect
import asyncio

@dataclass
class EventMethodInfo:
    """Information about an event method"""
    method_name: str
    method: Callable
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_async: bool = False
    parameters: List[str] = field(default_factory=list)

class EventCapable:
    """
    Event handling capabilities mixin.
    
    Provides infrastructure for entities to handle events through
    decorated methods, integrating with the event dispatcher system.
    """
    
    # Class-level event registry
    _event_methods: ClassVar[Dict[str, EventMethodInfo]] = {}
    _event_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {}
    
    def __init_subclass__(cls, **kwargs):
        """Register event methods when class is created"""
        super().__init_subclass__(**kwargs)
        cls._register_event_methods()
    
    @classmethod
    def _register_event_methods(cls):
        """Register all @event decorated methods for this class"""
        cls._event_methods = {}
        cls._event_metadata = {}
        
        # Scan class for event methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(method, '_event_metadata'):
                # This is an @event decorated method
                event_info = EventMethodInfo(
                    method_name=name,
                    method=method,
                    metadata=method._event_metadata,
                    is_async=inspect.iscoroutinefunction(method),
                    parameters=list(inspect.signature(method).parameters.keys())[1:]  # Skip 'self'
                )
                
                cls._event_methods[name] = event_info
                cls._event_metadata[name] = method._event_metadata
    
    @classmethod
    def get_event_methods(cls) -> Dict[str, EventMethodInfo]:
        """Get all event methods for this class"""
        return cls._event_methods.copy()
    
    @classmethod
    def get_event_metadata(cls, event_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific event"""
        return cls._event_metadata.get(event_name)
    
    @classmethod
    def has_event(cls, event_name: str) -> bool:
        """Check if this class has a specific event method"""
        return event_name in cls._event_methods
    
    async def execute_event(self, event_name: str, **kwargs) -> Any:
        """
        Execute an event method on this entity instance.
        
        Args:
            event_name: Name of the event method to execute
            **kwargs: Parameters to pass to the event method
            
        Returns:
            Result from the event method
            
        Raises:
            AttributeError: If event method doesn't exist
            TypeError: If invalid parameters provided
        """
        if event_name not in self._event_methods:
            raise AttributeError(f"Entity {self.__class__.__name__} has no event '{event_name}'")
        
        event_info = self._event_methods[event_name]
        method = getattr(self, event_name)
        
        # Validate parameters
        sig = inspect.signature(method)
        try:
            bound_args = sig.bind(self, **kwargs)
            bound_args.apply_defaults()
        except TypeError as e:
            raise TypeError(f"Invalid parameters for event '{event_name}': {e}")
        
        # Execute method
        if event_info.is_async:
            return await method(**kwargs)
        else:
            return method(**kwargs)
    
    def execute_event_sync(self, event_name: str, **kwargs) -> Any:
        """
        Synchronously execute an event method.
        
        Args:
            event_name: Name of the event method to execute
            **kwargs: Parameters to pass to the event method
            
        Returns:
            Result from the event method
        """
        if event_name not in self._event_methods:
            raise AttributeError(f"Entity {self.__class__.__name__} has no event '{event_name}'")
        
        event_info = self._event_methods[event_name]
        
        if event_info.is_async:
            # Run async method in event loop
            return asyncio.run(self.execute_event(event_name, **kwargs))
        else:
            # Execute sync method directly
            method = getattr(self, event_name)
            return method(**kwargs)
    
    # Event URL generation helpers
    @classmethod
    def get_event_url(cls, event_name: str, **params) -> str:
        """
        Generate URL for an event method.
        
        Args:
            event_name: Name of the event method
            **params: URL parameters
            
        Returns:
            URL string for the event
        """
        base_path = f"/entities/{cls.__name__.lower()}/events/{event_name}"
        
        if params:
            param_string = "&".join(f"{k}={v}" for k, v in params.items())
            return f"{base_path}?{param_string}"
        
        return base_path
    
    def get_instance_event_url(self, event_name: str, **params) -> str:
        """
        Generate URL for an event method on this specific instance.
        
        Args:
            event_name: Name of the event method
            **params: URL parameters
            
        Returns:
            URL string for the event
        """
        if hasattr(self, 'id') and self.id:
            base_path = f"/entities/{self.__class__.__name__.lower()}/{self.id}/events/{event_name}"
        else:
            base_path = f"/entities/{self.__class__.__name__.lower()}/events/{event_name}"
        
        if params:
            param_string = "&".join(f"{k}={v}" for k, v in params.items())
            return f"{base_path}?{param_string}"
        
        return base_path
    
    # Datastar integration helpers
    @classmethod
    def get_datastar_attributes(cls, event_name: str, **params) -> Dict[str, str]:
        """
        Get Datastar attributes for triggering an event.
        
        Args:
            event_name: Name of the event method
            **params: Event parameters
            
        Returns:
            Dictionary of Datastar attributes
        """
        if event_name not in cls._event_methods:
            raise AttributeError(f"Entity {cls.__name__} has no event '{event_name}'")
        
        event_info = cls._event_methods[event_name]
        metadata = event_info.metadata
        
        # Get event URL
        url = cls.get_event_url(event_name, **params)
        
        # Determine HTTP method
        method = metadata.get('method', 'POST').upper()
        
        # Determine trigger
        trigger = metadata.get('trigger', 'click')
        
        # Build Datastar attributes
        if method == 'GET':
            attr_name = f"data-on-{trigger}"
            attr_value = f"$get('{url}')"
        else:
            attr_name = f"data-on-{trigger}"
            attr_value = f"$post('{url}')"
        
        return {attr_name: attr_value}
    
    def get_instance_datastar_attributes(self, event_name: str, **params) -> Dict[str, str]:
        """
        Get Datastar attributes for triggering an event on this instance.
        
        Args:
            event_name: Name of the event method
            **params: Event parameters
            
        Returns:
            Dictionary of Datastar attributes
        """
        if event_name not in self._event_methods:
            raise AttributeError(f"Entity {self.__class__.__name__} has no event '{event_name}'")
        
        event_info = self._event_methods[event_name]
        metadata = event_info.metadata
        
        # Get event URL
        url = self.get_instance_event_url(event_name, **params)
        
        # Determine HTTP method
        method = metadata.get('method', 'POST').upper()
        
        # Determine trigger
        trigger = metadata.get('trigger', 'click')
        
        # Build Datastar attributes
        if method == 'GET':
            attr_name = f"data-on-{trigger}"
            attr_value = f"$get('{url}')"
        else:
            attr_name = f"data-on-{trigger}"
            attr_value = f"$post('{url}')"
        
        return {attr_name: attr_value}
    
    # Event validation and introspection
    def validate_event_parameters(self, event_name: str, **kwargs) -> bool:
        """
        Validate parameters for an event method.
        
        Args:
            event_name: Name of the event method
            **kwargs: Parameters to validate
            
        Returns:
            True if parameters are valid
            
        Raises:
            AttributeError: If event doesn't exist
            TypeError: If parameters are invalid
        """
        if event_name not in self._event_methods:
            raise AttributeError(f"Entity {self.__class__.__name__} has no event '{event_name}'")
        
        method = getattr(self, event_name)
        sig = inspect.signature(method)
        
        try:
            bound_args = sig.bind(self, **kwargs)
            bound_args.apply_defaults()
            return True
        except TypeError:
            return False
    
    @classmethod
    def get_event_signature(cls, event_name: str) -> Optional[inspect.Signature]:
        """
        Get the signature of an event method.
        
        Args:
            event_name: Name of the event method
            
        Returns:
            Method signature or None if event doesn't exist
        """
        if event_name not in cls._event_methods:
            return None
        
        event_info = cls._event_methods[event_name]
        return inspect.signature(event_info.method)

# Export main components
__all__ = ["EventCapable", "EventMethodInfo"]