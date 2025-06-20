"""
Event Commands - @event decorator and command definitions

🚀 Command-Based Architecture:
This module provides the @event decorator system that turns entity methods
into interactive commands. Events represent user actions and system commands
that trigger entity behavior.

Key Features:
- Pure metadata storage (no route registration)
- Rich event information for dispatchers
- Support for HTTP methods and Datastar integration
- Parameter extraction and validation
- Clean separation from web framework concerns
"""

import inspect
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List, Callable, Union
from enum import Enum

class EventMethod(Enum):
    """Supported HTTP methods for events"""
    GET = "GET"
    POST = "POST" 
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class MergeMode(Enum):
    """Datastar merge modes for UI updates"""
    MORPH = "morph"
    REPLACE = "replace"
    APPEND = "append"
    PREPEND = "prepend"
    BEFORE = "before"
    AFTER = "after"
    DELETE = "delete"

@dataclass
class EventMetadata:
    """
    Complete metadata about an event method.
    
    This is pure metadata - no framework-specific code.
    The dispatcher and adapters use this information to
    handle routing, execution, and response formatting.
    """
    name: str
    method: EventMethod = EventMethod.POST
    description: Optional[str] = None
    selector: Optional[str] = None
    merge_mode: MergeMode = MergeMode.MORPH
    path_template: Optional[str] = None
    signature: Optional[inspect.Signature] = None
    
    # Advanced options
    realtime: bool = True
    permissions: List[str] = field(default_factory=list)
    rate_limit: Optional[Dict[str, Any]] = None
    cache_ttl: Optional[int] = None
    include_in_schema: bool = True
    
    # Internal metadata
    original_function: Optional[Callable] = None
    entity_class: Optional[type] = None
    
    def to_url_pattern(self, entity_name: str) -> str:
        """Generate URL pattern for this event"""
        if self.path_template:
            return self.path_template.format(entity=entity_name.lower())
        return f"/{entity_name.lower()}/{self.name}"
    
    def get_http_method(self) -> str:
        """Get HTTP method as string"""
        return self.method.value
    
    def get_merge_mode(self) -> str:
        """Get merge mode as string"""
        return self.merge_mode.value

@dataclass
class CommandContext:
    """
    Context information for command execution.
    
    This provides all the information needed to execute
    an event method, without coupling to specific web frameworks.
    """
    entity_class: type
    entity_id: Optional[str]
    event_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Request context
    user_context: Optional[Dict[str, Any]] = None
    request_metadata: Optional[Dict[str, Any]] = None
    
    # Datastar payload (if applicable)
    datastar_payload: Optional['DatastarPayload'] = None
    
    # Execution context
    request_id: Optional[str] = None
    timestamp: Optional[str] = None

class DatastarPayload:
    """
    Represents Datastar payload data for reactive UI interactions.
    
    This class provides a clean interface to Datastar data
    without coupling to the web request format.
    """
    
    def __init__(self, data: Dict[str, Any] = None):
        self._data = data or {}
    
    def __getattr__(self, name: str) -> Any:
        """Allow accessing payload data as attributes"""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name)
    
    def __getitem__(self, key: str) -> Any:
        """Allow accessing payload data as dict items"""
        return self._data.get(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default"""
        return self._data.get(key, default)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in payload"""
        return key in self._data
    
    def keys(self):
        """Get all keys in payload"""
        return self._data.keys()
    
    def values(self):
        """Get all values in payload"""
        return self._data.values()
    
    def items(self):
        """Get all key-value pairs in payload"""
        return self._data.items()
    
    @property
    def raw_data(self) -> Dict[str, Any]:
        """Access the raw data dictionary"""
        return self._data
    
    def __repr__(self) -> str:
        return f"DatastarPayload({self._data})"

class EventCapable:
    """
    Mixin for entities that can have @event methods.
    
    Provides utilities for working with events on entity classes.
    """
    
    @classmethod
    def get_events(cls) -> Dict[str, EventMetadata]:
        """Get all @event methods on this entity"""
        events = {}
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_event_metadata'):
                events[attr_name] = attr._event_metadata
        return events
    
    @classmethod
    def get_event(cls, event_name: str) -> Optional[EventMetadata]:
        """Get specific event metadata by name"""
        events = cls.get_events()
        return events.get(event_name)
    
    def get_event_method(self, event_name: str) -> Optional[Callable]:
        """Get event method by name"""
        if event_name in self.get_events():
            return getattr(self, event_name)
        return None
    
    @classmethod
    def has_event(cls, event_name: str) -> bool:
        """Check if entity has a specific event"""
        return event_name in cls.get_events()

def event(
    fn: Optional[Callable] = None,
    *,
    method: Union[str, EventMethod] = EventMethod.POST,
    description: Optional[str] = None,
    selector: Optional[str] = None,
    merge_mode: Union[str, MergeMode] = MergeMode.MORPH,
    path: Optional[str] = None,
    realtime: bool = True,
    permissions: Optional[List[str]] = None,
    rate_limit: Optional[Dict[str, Any]] = None,
    cache_ttl: Optional[int] = None,
    include_in_schema: bool = True
) -> Callable:
    """
    Mark a method as an interactive event.
    
    Events are the primary way users interact with entities.
    They automatically become:
    - HTTP endpoints for web interactions
    - Real-time synchronized actions  
    - UI-bound interactive elements
    
    Args:
        fn: Function being decorated (when used without parentheses)
        method: HTTP method for the event
        description: Human-readable description of what this event does
        selector: CSS selector for Datastar fragment updates
        merge_mode: How Datastar should merge UI updates
        path: Custom path template (uses /{entity}/{event} by default)
        realtime: Whether this event should trigger real-time updates
        permissions: List of required permissions to execute this event
        rate_limit: Rate limiting configuration
        cache_ttl: Cache TTL for response (if applicable)
        include_in_schema: Whether to include in API schema
        
    Returns:
        Decorated function with _event_metadata attribute
        
    Example:
        class BlogPost(Entity):
            title: str
            published: bool = False
            
            @event(description="Publish this blog post")
            async def publish(self):
                self.published = True
                
            @event(
                method=EventMethod.POST,
                description="Add a comment to this post",
                realtime=True,
                permissions=["comment.create"]
            )
            async def add_comment(self, content: str, author: str):
                # Implementation here
                pass
    """
    def decorator(func: Callable) -> Callable:
        # Normalize method
        if isinstance(method, str):
            event_method = EventMethod(method.upper())
        else:
            event_method = method
            
        # Normalize merge mode
        if isinstance(merge_mode, str):
            event_merge_mode = MergeMode(merge_mode.lower())
        else:
            event_merge_mode = merge_mode
        
        # Create event metadata
        metadata = EventMetadata(
            name=func.__name__,
            method=event_method,
            description=description or f"Execute {func.__name__} event",
            selector=selector,
            merge_mode=event_merge_mode,
            path_template=path,
            signature=inspect.signature(func),
            realtime=realtime,
            permissions=permissions or [],
            rate_limit=rate_limit,
            cache_ttl=cache_ttl,
            include_in_schema=include_in_schema,
            original_function=func
        )
        
        # Store metadata on function
        func._event_metadata = metadata
        
        # Legacy compatibility
        func._event_info = metadata  # Old attribute name
        
        return func
    
    # Handle usage as @event without parentheses
    if fn is not None:
        return decorator(fn)
    
    return decorator

# URL Generator Descriptor (for Datastar attributes)
class EventMethodDescriptor:
    """
    Descriptor that generates URLs for event methods in Datastar attributes.
    
    When accessed as a class attribute, this generates the appropriate
    URL or Datastar attribute string for the event.
    """
    
    def __init__(self, event_name: str, entity_name: str, original_method: Callable):
        self.event_name = event_name
        self.entity_name = entity_name
        self.original_method = original_method
        self.event_metadata = getattr(original_method, '_event_metadata', None)
    
    def __get__(self, instance, owner):
        if instance is not None:
            # Called on instance - return the bound method
            return self.original_method.__get__(instance, owner)
        else:
            # Called on class - return URL generator
            return self._create_url_generator(owner)
    
    def _create_url_generator(self, entity_class):
        """Create URL generator function for this event"""
        
        def url_generator(*args, **kwargs):
            """Generate URL for this event with parameters"""
            if self.event_metadata:
                base_url = self.event_metadata.to_url_pattern(self.entity_name)
            else:
                base_url = f"/{self.entity_name.lower()}/{self.event_name}"
            
            # Add parameters as query string
            if args or kwargs:
                # Convert positional args to kwargs based on signature
                if self.event_metadata and self.event_metadata.signature:
                    param_names = list(self.event_metadata.signature.parameters.keys())[1:]  # Skip 'self'
                    for i, arg in enumerate(args):
                        if i < len(param_names):
                            kwargs[param_names[i]] = arg
                
                # Build query string
                if kwargs:
                    query_parts = [f"{k}={v}" for k, v in kwargs.items()]
                    query_string = "&".join(query_parts)
                    return f"{base_url}?{query_string}"
            
            return base_url
        
        # Add metadata to the generator
        url_generator._event_metadata = self.event_metadata
        url_generator._is_url_generator = True
        
        return url_generator

# Utility functions for Datastar integration
def extract_datastar_payload(request) -> DatastarPayload:
    """
    Extract Datastar payload from request.
    
    This function will be moved to the web adapter layer
    once the migration is complete.
    """
    try:
        # Try to get from query params first
        datastar_json = getattr(request, 'query_params', {}).get('datastar')
        
        if not datastar_json and hasattr(request, 'form'):
            # Try to get from form data
            form_data = getattr(request, 'form', {})
            datastar_json = form_data.get('datastar')
        
        if datastar_json:
            import json
            data = json.loads(datastar_json)
            return DatastarPayload(data)
            
    except Exception:
        # If extraction fails, return empty payload
        pass
    
    return DatastarPayload()

# Legacy compatibility functions
def datastar_from_queryParams(request) -> DatastarPayload:
    """Legacy function - use extract_datastar_payload instead"""
    return extract_datastar_payload(request)

# Export main components
__all__ = [
    "event", "EventMetadata", "EventMethod", "MergeMode",
    "CommandContext", "DatastarPayload", "EventCapable",
    "EventMethodDescriptor", "extract_datastar_payload",
    # Legacy compatibility
    "datastar_from_queryParams"
]