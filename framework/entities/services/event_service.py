"""
Event Service - Entity Event Processing

🚀 Event-Driven Behavior:
This service handles event method processing for entities, providing clean separation
between event execution logic and entity business logic through dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Callable, TYPE_CHECKING
import inspect
import asyncio

if TYPE_CHECKING:
    from ..lifecycle.entity import Entity

from ...events.commands.event import EventMetadata
from ...events.dispatching.command_context import CommandContext, CommandResult


class EventService(ABC):
    """
    Abstract interface for entity event processing.
    
    This service is injected into entities to handle event method execution,
    keeping the entity focused on business logic while delegating event
    processing concerns to this service.
    """
    
    @abstractmethod
    async def execute_event(self, entity: 'Entity', event_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute an event method on an entity"""
        pass
    
    @abstractmethod
    def get_entity_events(self, entity_class: Type['Entity']) -> Dict[str, EventMetadata]:
        """Get all event methods for an entity class"""
        pass
    
    @abstractmethod
    def has_event(self, entity_class: Type['Entity'], event_name: str) -> bool:
        """Check if entity class has a specific event"""
        pass
    
    @abstractmethod
    def setup_entity_events(self, entity_class: Type['Entity']):
        """Set up event methods for an entity class"""
        pass
    
    @abstractmethod
    def create_url_generator(self, entity_class: Type['Entity'], event_name: str) -> Callable:
        """Create URL generator for an event method"""
        pass


class EntityEventService(EventService):
    """
    Default implementation of event service with full event processing capabilities.
    
    This service integrates with the event dispatcher and provides URL generation
    for web framework integration.
    """
    
    def __init__(self, event_dispatcher=None):
        self.event_dispatcher = event_dispatcher
        self._event_metadata_cache: Dict[Type, Dict[str, EventMetadata]] = {}
    
    async def execute_event(self, entity: 'Entity', event_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute an event method on an entity"""
        # Get the event method
        if not hasattr(entity, event_name):
            raise ValueError(f"Entity {type(entity).__name__} has no event '{event_name}'")
        
        event_method = getattr(entity, event_name)
        
        # Check if it's actually an event method
        if not hasattr(event_method, '_event_metadata'):
            raise ValueError(f"Method '{event_name}' is not an event method")
        
        # Prepare parameters for method call
        method_signature = inspect.signature(event_method)
        bound_args = method_signature.bind_partial(**parameters)
        bound_args.apply_defaults()
        
        # Execute the method
        if asyncio.iscoroutinefunction(event_method):
            result = await event_method(**bound_args.arguments)
        else:
            result = event_method(**bound_args.arguments)
        
        return result
    
    def get_entity_events(self, entity_class: Type['Entity']) -> Dict[str, EventMetadata]:
        """Get all event methods for an entity class with caching"""
        if entity_class not in self._event_metadata_cache:
            events = {}
            for attr_name in dir(entity_class):
                attr = getattr(entity_class, attr_name)
                if hasattr(attr, '_event_metadata'):
                    events[attr_name] = attr._event_metadata
            self._event_metadata_cache[entity_class] = events
        
        return self._event_metadata_cache[entity_class]
    
    def has_event(self, entity_class: Type['Entity'], event_name: str) -> bool:
        """Check if entity class has a specific event"""
        events = self.get_entity_events(entity_class)
        return event_name in events
    
    def setup_entity_events(self, entity_class: Type['Entity']):
        """Set up event methods for an entity class"""
        # Create URL generator methods for all @event decorated methods
        events = self.get_entity_events(entity_class)
        
        for event_name, metadata in events.items():
            # Create URL generator method
            url_generator = self.create_url_generator(entity_class, event_name)
            
            # Store original method and replace with descriptor
            original_method = getattr(entity_class, event_name)
            
            class EventMethodDescriptor:
                """Descriptor that provides both method execution and URL generation"""
                
                def __init__(self, original_method, url_generator, event_service):
                    self.original_method = original_method
                    self.url_generator = url_generator
                    self.event_service = event_service
                
                def __get__(self, instance, owner):
                    if instance is not None:
                        # Return bound method when accessed on instance
                        return self.original_method.__get__(instance, owner)
                    else:
                        # Return URL generator when accessed on class
                        return self.url_generator
                
                def __set__(self, instance, value):
                    # Prevent setting
                    raise AttributeError("Cannot set event method")
            
            descriptor = EventMethodDescriptor(original_method, url_generator, self)
            setattr(entity_class, event_name, descriptor)
    
    def create_url_generator(self, entity_class: Type['Entity'], event_name: str) -> Callable:
        """Create URL generator for an event method"""
        
        def url_generator(*args, **kwargs):
            """Generate URL for this event with parameters"""
            # Basic URL pattern
            base_url = f"/{entity_class.__name__.lower()}/{event_name}"
            
            # Add parameters as query string if provided
            if args or kwargs:
                # Convert positional args to kwargs based on method signature
                events = self.get_entity_events(entity_class)
                if event_name in events:
                    metadata = events[event_name]
                    if metadata.signature:
                        param_names = list(metadata.signature.parameters.keys())[1:]  # Skip 'self'
                        for i, arg in enumerate(args):
                            if i < len(param_names):
                                kwargs[param_names[i]] = arg
                
                # Build query string
                if kwargs:
                    query_parts = [f"{k}={v}" for k, v in kwargs.items()]
                    query_string = "&".join(query_parts)
                    return f"{base_url}?{query_string}"
            
            return base_url
        
        # Add metadata to generator
        events = self.get_entity_events(entity_class)
        if event_name in events:
            url_generator._event_metadata = events[event_name]
        
        return url_generator


class SimpleEventService(EventService):
    """
    Simple event service for testing and minimal deployments.
    
    This implementation provides basic event execution without
    complex URL generation or dispatcher integration.
    """
    
    async def execute_event(self, entity: 'Entity', event_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute event method directly"""
        if not hasattr(entity, event_name):
            raise ValueError(f"Entity has no method '{event_name}'")
        
        method = getattr(entity, event_name)
        
        # Execute with parameters
        if asyncio.iscoroutinefunction(method):
            return await method(**parameters)
        else:
            return method(**parameters)
    
    def get_entity_events(self, entity_class: Type['Entity']) -> Dict[str, EventMetadata]:
        """Get event methods (simplified)"""
        events = {}
        for attr_name in dir(entity_class):
            attr = getattr(entity_class, attr_name)
            if hasattr(attr, '_event_metadata'):
                events[attr_name] = attr._event_metadata
        return events
    
    def has_event(self, entity_class: Type['Entity'], event_name: str) -> bool:
        """Check if entity has event"""
        return event_name in self.get_entity_events(entity_class)
    
    def setup_entity_events(self, entity_class: Type['Entity']):
        """Simple event setup"""
        # For simple implementation, events work as regular methods
        pass
    
    def create_url_generator(self, entity_class: Type['Entity'], event_name: str) -> Callable:
        """Create simple URL generator"""
        def simple_generator(*args, **kwargs):
            return f"/{entity_class.__name__.lower()}/{event_name}"
        
        return simple_generator


# Export main components
__all__ = [
    "EventService", "EntityEventService", "SimpleEventService"
]