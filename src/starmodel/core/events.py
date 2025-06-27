"""
Simplified Event Decorator System

This module provides the @event decorator that stores metadata only.
Route registration is handled by the dispatcher and FastHTML adapter.

This is the refactored version as specified in app-layer.md.
"""

import inspect
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, Type, TypeVar

T = TypeVar('T')

@dataclass
class EventInfo:
    """Metadata about an event method stored by the @event decorator."""
    name: str
    method: str
    selector: Optional[str]
    merge_mode: str
    signature: inspect.Signature
    path: Optional[str] = None
    include_in_schema: bool = True
    namespace: Optional[str] = None
    entity_class: Optional[Type[T]] = None
    kwargs: dict = field(default_factory=dict)


class DatastarPayload:
    """Represents Datastar payload data that can be injected into event methods."""
    
    def __init__(self, data: Dict[str, Any] = None):
        self._data = data or {}
    
    def __getattr__(self, name: str) -> Any:
        """Allow accessing payload data as attributes."""
        return self._data.get(name)
    
    def __getitem__(self, key: str) -> Any:
        """Allow accessing payload data as dict items."""
        return self._data.get(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default."""
        return self._data.get(key, default)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in payload."""
        return key in self._data
    
    def __repr__(self) -> str:
        return f"DatastarPayload({self._data})"
    
    @property
    def raw_data(self) -> Dict[str, Any]:
        """Access the raw data dictionary."""
        return self._data


def event(
    fn=None, 
    *, 
    method: str = "GET", 
    selector: Optional[str] = None,
    merge_mode: str = "morph",
    path: Optional[str] = None,
    include_in_schema: bool = True,
    **kwargs
):
    """
    Store event metadata only - no route registration.
    
    The @event decorator now only stores metadata about the method.
    Actual route registration is handled by the FastHTML adapter.
    
    Args:
        fn: Function being decorated (when used without parentheses)
        method: HTTP method for the event (GET, POST, etc.)
        selector: CSS selector for Datastar fragment updates
        merge_mode: Datastar merge mode (morph, replace, etc.)
        path: Custom path for the route (optional)
        include_in_schema: Whether to include in API schema
    
    Returns:
        Decorated function with _event_info attribute
    """
    def decorator(func):
        # Store event metadata on the function
        func._event_info = EventInfo(
            name=func.__name__,
            method=method.upper(), # TODO: make this a list of methods
            selector=selector, # Datastar selector
            merge_mode=merge_mode, # Datastar merge mode
            signature=inspect.signature(func), # Event method signature
            path=path, # Custom path for the route
            include_in_schema=include_in_schema, # Whether to include in API schema
            kwargs=kwargs # Additional keyword arguments
        )
        return func
    
    # Handle usage as @event without parentheses
    if fn is not None:
        return decorator(fn)
    
    return decorator


# Legacy compatibility - keep the old DatastarPayload extraction functions
# These will be moved to the dispatcher in a future cleanup

def datastar_from_queryParams(request) -> DatastarPayload:
    """Extract Datastar payload from request query params only."""
    import json
    
    try:
        datastar_json_str = request.query_params.get('datastar')
        if datastar_json_str:
            data = json.loads(datastar_json_str)
            return DatastarPayload(data)
    except Exception:
        pass
    
    return DatastarPayload()


# Note: extract_datastar_payload was removed as it's not used in the new architecture