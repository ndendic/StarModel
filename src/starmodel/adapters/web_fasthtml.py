"""
FastHTML Web Adapter

Implements clean integration between StarModel entities and FastHTML routing.
Replaces direct route registration in @event decorators with clean adapter pattern.
"""

from typing import Any, Type, Callable
from fasthtml.common import Request, JSONResponse, StreamingResponse, FT, to_xml
import inspect
import asyncio

# Import Datastar SSE functionality
try:
    from datastar_py import SSE_HEADERS
    from datastar_py import ServerSentEventGenerator as SSE
except ImportError:
    # Fallback if datastar_py is not available
    SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    class SSE:
        @staticmethod
        def merge_signals(signals):
            return f"data: merge_signals {signals}\n\n"
        
        @staticmethod
        def merge_fragments(fragment, selector=None, merge_mode="morph"):
            return f"data: merge_fragments {fragment}\n\n"

from ..app.dispatcher import call_event, is_datastar_request
from ..app.uow import UnitOfWork
from ..core.entity import Entity


def include_entity(
    router, 
    entity_class: Type[Entity], 
    uow: UnitOfWork,
    base_path: str = None
) -> None:
    """
    Register entity events as FastHTML routes via the dispatcher pattern.
    
    This function replaces the direct route registration that was previously
    done in the @event decorator, implementing clean separation of concerns.
    
    Args:
        router: FastHTML router function (rt)
        entity_class: Entity class containing @event methods
        uow: Unit of Work instance for transaction management
        base_path: Optional base path for routes (defaults to entity class name)
    """
    if base_path is None:
        base_path = entity_class.__name__.lower()
    
    # Find all event methods on the entity class
    events = _discover_events(entity_class)
    
    for event_name, event_info in events.items():
        # Create route path
        path = f"/{base_path}/{event_name}"
        
        # Create route handler that uses the dispatcher
        handler = _create_route_handler(entity_class, event_name, uow)
        
        # Register route with FastHTML using decorator pattern
        method = event_info.method if hasattr(event_info, 'method') else 'GET'
        
        # Use FastHTML's route decorator pattern
        router(path, methods=[method])(handler)


def _discover_events(entity_class: Type[Entity]) -> dict:
    """
    Discover all @event decorated methods on an entity class.
    
    Args:
        entity_class: Entity class to inspect
        
    Returns:
        Dictionary mapping event names to event metadata
    """
    events = {}
    
    # Inspect all methods on the class
    for name in dir(entity_class):
        method = getattr(entity_class, name)
        
        # Check if method has event metadata (added by @event decorator)
        if hasattr(method, '_event_info'):
            events[name] = method._event_info
    
    return events


def _create_route_handler(
    entity_class: Type[Entity], 
    event_name: str, 
    uow: UnitOfWork
) -> Callable:
    """
    Create a route handler function for an entity event.
    
    Args:
        entity_class: Entity class containing the event
        event_name: Name of the event method
        uow: Unit of Work for transaction management
        
    Returns:
        Async function suitable for FastHTML route registration
    """
    async def handler(request: Request):
        """Route handler that executes entity events via dispatcher."""
        try:
            # Use dispatcher to execute the command (now async)
            new_entity, command_record = await call_event(entity_class, event_name, request)
            
            # Commit changes via Unit of Work
            await uow.commit(new_entity, command_record)
            
            # Convert command result to appropriate response
            return await _command_to_response(command_record, new_entity, request)
            
        except Exception as e:
            # Return error message as string for FastHTML
            return f"Error executing {event_name}: {str(e)}"
    
    return handler


async def _command_to_response(
    command_record: dict, 
    entity: Entity, 
    request: Request
):
    """
    Convert command execution result to appropriate HTTP response.
    
    This function determines whether to return:
    - Datastar SSE response with merge_signals and merge_fragments
    - JSON response for API requests  
    - HTML fragments for direct returns
    
    Args:
        command_record: Command execution record from dispatcher
        entity: Updated entity state
        request: Original HTTP request
        
    Returns:
        Appropriate response content for FastHTML
    """
    # Check if this is a Datastar request (has datastar in query params or form)
    is_datastar = await is_datastar_request(request)
    if is_datastar:
        result = command_record.get('result')
        event_info = command_record.get('event_info')
        
        # Get event configuration for selector and merge_mode
        selector = getattr(event_info, 'selector', None) if event_info else None
        merge_mode = getattr(event_info, 'merge_mode', 'morph') if event_info else 'morph'
        
        # Create proper SSE response following the original pattern
        async def sse_stream():
            # Always send current entity signals first
            yield SSE.merge_signals(entity.signals)
            
            if hasattr(result, '__aiter__'):  # Async generator
                async for item in result:
                    # Auto-persist entity changes after each yield if configured
                    if hasattr(entity, 'auto_persist') and entity.auto_persist and not getattr(entity, 'store', '').startswith("client_"):
                        entity.save()
                    
                    # Send updated entity signals after each yield
                    yield SSE.merge_signals(entity.signals)
                    
                    # Handle HTML fragments
                    if item and (hasattr(item, '__ft__') or isinstance(item, FT)):
                        fragment = to_xml(item)
                        if selector:
                            yield SSE.merge_fragments(fragment, selector=selector, merge_mode=merge_mode)
                        else:
                            yield SSE.merge_fragments(fragment, merge_mode=merge_mode)
                            
            elif hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):  # Regular generator
                for item in result:
                    # Auto-persist entity changes after each yield if configured
                    if hasattr(entity, 'auto_persist') and entity.auto_persist and not getattr(entity, 'store', '').startswith("client_"):
                        entity.save()
                    
                    # Send updated entity signals after each yield
                    yield SSE.merge_signals(entity.signals)
                    
                    # Handle HTML fragments
                    if item and (hasattr(item, '__ft__') or isinstance(item, FT)):
                        fragment = to_xml(item)
                        if selector:
                            yield SSE.merge_fragments(fragment, selector=selector, merge_mode=merge_mode)
                        else:
                            yield SSE.merge_fragments(fragment, merge_mode=merge_mode)
                            
            else:  # Regular return or None
                if result and (hasattr(result, '__ft__') or isinstance(result, FT)):
                    fragment = to_xml(result)
                    if selector:
                        yield SSE.merge_fragments(fragment, selector=selector, merge_mode=merge_mode)
                    else:
                        yield SSE.merge_fragments(fragment, merge_mode=merge_mode)
        
        return StreamingResponse(sse_stream(), media_type="text/event-stream", headers=SSE_HEADERS)
    
    # Check if this is an API request (accepts JSON)
    if 'application/json' in request.headers.get('accept', ''):
        # Return JSON response with entity state
        return JSONResponse({
            'success': True,
            'entity': entity.model_dump() if hasattr(entity, 'model_dump') else str(entity),
            'command': command_record['event']
        })
    
    # Default: return success message
    return f"Command {command_record['event']} executed successfully"


def register_entities(router, entity_classes: list, uow: UnitOfWork) -> None:
    """
    Convenience function to register multiple entity classes at once.
    
    Args:
        router: FastHTML router function (rt)
        entity_classes: List of entity classes to register
        uow: Unit of Work instance
    """
    for entity_class in entity_classes:
        include_entity(router, entity_class, uow)

def register_all_entities(router) -> None:
    """
    Register all entities in the current module.
    """
    try:
        from starmodel import UnitOfWork, InProcessBus, persistence_manager
        uow = UnitOfWork(persistence_manager, InProcessBus())
        for e in Entity.__subclasses__():
            include_entity(router, e, uow)
    except Exception as e:
        print(f"Error registering all entities: {e}")



