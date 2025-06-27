"""
Command Dispatcher

Core command execution system that replaces direct @event route handling.
Implements the APPLICATION SERVICE LAYER pattern from clean architecture.
"""

import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Tuple, Type, AsyncGenerator
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastcore.xml import FT, to_xml
from datastar_py.fastapi import DatastarResponse

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

from .utils import _find_p, _fix_anno, parse_form
from ..core import DatastarPayload
from ..core.entity import Entity
from ..core.events import EventInfo
from ..app.uow import UnitOfWork
from ..app.bus import InProcessBus, EventBus
from ..app.datastar import is_datastar_request, explode_datastar_params_in_request
from starlette.middleware.base import BaseHTTPMiddleware, DispatchFunction
from starlette.types import ASGIApp
from starlette.applications import Starlette

class Dispatcher:
    """
    Base dispatcher class for handling entity event routing and execution.
    
    This is the core orchestrator that:
    1. Discovers @event methods on entity classes and stores them in a dictionary
    2. Creates route handlers for web frameworks
    3. Executes commands via call_event
    4. Converts results to appropriate responses
    """
    
    def __init__(self, uow: UnitOfWork = None, bus: EventBus = InProcessBus()):
        self.namespace_routes = {}
        self.bus = bus
        self.uow = uow or UnitOfWork(self.bus)
    
    def _register_route(self, router, path: str, handler: Callable, event_info: EventInfo):
        """
        Register a route with the framework router.
        
        Base implementation - MUST be overridden by framework-specific dispatchers.
        """
        raise NotImplementedError("Subclasses must implement _register_route")
    
    def discover_events(self, entity_class: Type[Entity]) -> Dict[str, EventInfo]:
        """Discover all @event decorated methods on an entity class."""
        events = {}
        # Inspect all methods on the class
        for name in dir(entity_class):
            method = getattr(entity_class, name)            
            if hasattr(method, '_event_info'): events[name] = method._event_info
        return events
    
    def include_entity(self, router, entity_class: Type[Entity], base_path: str = "") -> None:
        """
        Register a single entity class with the router.
        
        Args:
            router: Framework router
            entity_class: Entity class containing @event methods
            base_path: Optional base path for routes
        """
        # Find all event methods on the entity class
        events = self.discover_events(entity_class)
        
        for event_name, event_info in events.items():
            # Create route path if not provided
            namespace = getattr(entity_class, '_namespace', entity_class.__name__)
            event_path = event_info.path if event_info.path else f"/{namespace.lower()}/{event_name}"
            path = f"/{base_path}/{event_path}" if base_path else event_path
            # Store namespace mapping for middleware
            self.namespace_routes[path] = namespace            
            # Create route handler
            handler = self._create_route_handler(entity_class, event_name, event_info)            
            # Register route (framework-specific)
            self._register_route(router, path, handler, event_info)

    def include_entities(self, router, entity_classes: list = None, base_path: str = ""):
        """Register multiple entity classes with the router."""
        if not entity_classes:
            entity_classes = Entity.__subclasses__()        
        for entity_class in entity_classes:
            self.include_entity(router, entity_class, base_path)    
    
    def _create_route_handler(self,entity_class: Type[Entity],event_name: str, event_info: EventInfo) -> Callable:
        """
        Create a route handler function for an entity event.
        Base implementation - can be overridden by framework-specific dispatchers.        
        """
        async def handler(*args, **kwargs):
            """Route handler that executes entity events via dispatcher."""
            try:
                request, resolved_args, resolved_kwargs = self._resolve_args(args, kwargs) # Resolve request, args, kwargs
                entity = entity_class.get(request)
                event_function = getattr(entity_class, event_name)
                new_entity, command_record = await self.call_event(entity, event_function, request, *resolved_args, **resolved_kwargs) # Execute event
                await self.uow.commit(new_entity, command_record) # Commit changes via Unit of Work            
                return await self.command_to_response(command_record, new_entity, request) # Convert command result to appropriate response
            except Exception as e:
                # TODO: log error
                return f"Error executing {event_name}: {str(e)}" # Return generic error message
            
        handler._event_info = event_info # Store event info on the handler as well
        handler._entity_class = entity_class # Store entity class on the handler as well
        return handler
    
    def _get_event_function(self, entity_class: Type[Entity], event_name: str) -> Callable:
        """Get the event function from the entity class."""
        event_function = getattr(entity_class, event_name)
        if hasattr(event_function, 'original_method'):
            return event_function.original_method
        return event_function
    
    async def _fix_args(self, entity: Entity, event_info: EventInfo, request: Request, namespace: str) -> Tuple[Any, Dict]:
        wrapped_params = await _wrap_req_with_datastar(request, event_info.signature.parameters, namespace=namespace)
        method_params = [entity] + wrapped_params[1:]
        return method_params

    async def call_event(self, entity: Entity, event_function: Callable, request: Request, *resolved_args, **resolved_kwargs) -> Tuple[Any, Dict]:
        """This function implements the command dispatcher pattern for executing events."""

        event_info = event_function._event_info
        # if resolved_args or resolved_kwargs:
        if inspect.iscoroutinefunction(event_function):
            result = await event_function(entity, *resolved_args, **resolved_kwargs)
        else:
            result = event_function(entity, *resolved_args, **resolved_kwargs)        

        # If the method returned a new entity state, use it; otherwise use the original
        if hasattr(result, '__dict__') and hasattr(result, 'id'):
            new_entity = result
        else:
            new_entity = entity
        
        # Create synthetic command record for event bus and debugging
        # Build args dict from method signature and resolved parameters
        command_record = {
            "entity": f"{entity.__class__.__name__}:{entity.id}",
            "event": str(event_function),
            "args": resolved_args,
            "actor": None,  # Simplified for now
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": result,
            "event_info": event_info,  # Include event info for response handling
        }
        
        return new_entity, command_record
    
    def _resolve_args(self, args: list, kwargs: dict) -> Tuple[Request, list, dict]:
        """Find request object in args or kwargs, remove it from args and kwargs and return request, args, kwargs."""
        request = None
        for i, arg in enumerate(args):
            if isinstance(arg, Request):
                request = args[i]
                args = args[:i] + args[i+1:]
                break
        for k, v in kwargs.items():
            if isinstance(v, Request):
                request = v
                kwargs.pop(k)
                break
        return request, args, kwargs

    async def command_to_response(self, command_record: Dict[str, Any],entity: Entity, request: Request) -> Any:
        """
        Convert command execution result to appropriate HTTP response.
        
        Base implementation that handles:
        - Datastar SSE responses with merge_signals and merge_fragments
        - JSON responses for API requests  
        - Default string responses
        
        Can be overridden by framework-specific dispatchers for customization.
        
        Args:
            command_record: Command execution record from dispatcher
            entity: Updated entity state
            request: Original HTTP request
            
        Returns:
            Appropriate response for the web framework
        """
        # Check if this is a Datastar request
        is_datastar = await is_datastar_request(request)
        if is_datastar:
            result = command_record.get('result')
            event_info = command_record.get('event_info')
            
            # Get event configuration for selector and merge_mode
            selector = getattr(event_info, 'selector', None) if event_info else None
            merge_mode = getattr(event_info, 'merge_mode', 'morph') if event_info else 'morph'
            
            # Create SSE stream
            sse_stream = self._create_sse_stream(result, entity, selector, merge_mode)
            return DatastarResponse(sse_stream)
        
        # Check if this is an API request (accepts JSON)
        if 'application/json' in request.headers.get('accept', ''):
            # Return JSON response with entity state
            return JSONResponse({
                'success': True,
                'entity': entity.model_dump() if hasattr(entity, 'model_dump') else str(entity),
                'command': command_record['event']
            })
        
        # Default: return the result directly
        return command_record.get('result', f"Command {command_record['event']} executed successfully")
    
    async def _create_sse_stream(
        self,
        result: Any, 
        entity: Entity, 
        selector: str = None, 
        merge_mode: str = 'morph'
    ) -> AsyncGenerator[str, None]:
        """Create Server-Sent Event stream for Datastar responses."""
        # Always send current entity signals first
        yield SSE.merge_signals(entity.signals)
        
        if hasattr(result, '__aiter__'):  # Async generator
            async for item in result:
                async for sse_event in self._handle_stream_item(item, entity, selector, merge_mode):
                    yield sse_event
                        
        elif hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):  # Regular generator
            for item in result:
                async for sse_event in self._handle_stream_item(item, entity, selector, merge_mode):
                    yield sse_event
                        
        else:  # Single result or None
            async for sse_event in self._handle_single_result(result, selector, merge_mode):
                yield sse_event
    
    async def _handle_stream_item(
        self,
        item: Any, 
        entity: Entity, 
        selector: str = None, 
        merge_mode: str = 'morph'
    ) -> AsyncGenerator[str, None]:
        """Handle a single item from a generator stream."""
        # Auto-persist entity changes after each yield if configured
        self._auto_persist_entity(entity)
        
        # Send updated entity signals after each yield
        yield SSE.merge_signals(entity.signals)
        
        # Handle HTML fragments
        fragment = self._render_fragment(item)
        if fragment:
            yield self._create_fragment_event(fragment, selector, merge_mode)
    
    async def _handle_single_result(
        self,
        result: Any, 
        selector: str = None, 
        merge_mode: str = 'morph'
    ) -> AsyncGenerator[str, None]:
        """Handle a single result (non-generator)."""
        fragment = self._render_fragment(result)
        if fragment:
            yield self._create_fragment_event(fragment, selector, merge_mode)
        else:
            yield self._create_fragment_event(str(result), selector, merge_mode)
    
    def _auto_persist_entity(self, entity: Entity) -> None:
        """Auto-persist entity if configured to do so."""
        if (hasattr(entity, 'auto_persist') and entity.auto_persist and 
            not getattr(entity, 'store', '').startswith("client_")):
            entity.save()
    
    def _create_fragment_event(
        self,
        fragment: str, 
        selector: str = None, 
        merge_mode: str = 'morph'
    ) -> str:
        """Create a properly formatted SSE fragment event."""
        if selector:
            return SSE.merge_fragments(fragment, selector=selector, merge_mode=merge_mode)
        else:
            return SSE.merge_fragments(fragment, merge_mode=merge_mode)
    
    def _render_fragment(self, item: Any) -> str:
        """
        Render an item to HTML fragment string.
        
        Can be overridden by framework-specific dispatchers.
        
        Args:
            item: Object to render as HTML fragment
            
        Returns:
            HTML fragment string or None if not renderable
        """
        if not item:
            return None
            
        # Fall back to FastCore's to_xml for FT objects (FastHTML prefers this)
        if hasattr(item, '__ft__') or isinstance(item, FT):
            return to_xml(item)

        # Try .render() method for other objects
        if hasattr(item, 'render'):
            return item.render()
            
        # Handle string/bytes directly
        if isinstance(item, (str, bytes)):
            return str(item)
            
        return None

class DatastarMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp, dispatch: DispatchFunction | None = None, dispatcher: Dispatcher = None) -> None:
        super().__init__(app, dispatch)
        self.dispatcher = dispatcher

    async def dispatch(self, request, call_next):
        if await is_datastar_request(request):
            path = request.scope["path"]
            namespace = self.dispatcher.namespace_routes.get(path, None)
            if namespace:
                await explode_datastar_params_in_request(request, namespace)
        return await call_next(request)

def setup_datastar_middleware(app: Starlette, dispatcher: Dispatcher):
    """Set up FastHTML middleware for datastar parameter extraction."""
    app.add_middleware(DatastarMiddleware, dispatcher=dispatcher)
    return app


# Helpers for manual parameter resolution
async def _extract_datastar_payload(request: Request) -> DatastarPayload:
    """
    Extract Datastar payload from request using unified approach.
    
    Uses the same logic as explode_datastar_params_in_request for consistency.
    """
    try:
        from datastar_py.fastapi import read_signals
        datastar_payload = await read_signals(request)
        return DatastarPayload(datastar_payload)
    except Exception:
        return DatastarPayload(None)


async def _find_p_with_datastar(req: Request, arg: str, p, datastar_payload):
    """Extended version of FastHTML's _find_p that also supports Datastar parameters."""
    from ..core.events import DatastarPayload
    
    anno = p.annotation
    
    # Handle special event parameters and query params first
    if arg.lower() == 'request' or arg.lower() == 'req': 
        return req
    if arg.lower() == 'datastar' or (anno is DatastarPayload or anno == DatastarPayload): 
        return datastar_payload
    elif arg in req.query_params:
        value = req.query_params[arg]
        if anno != inspect.Parameter.empty:
            try:
                return _fix_anno(anno, value)
            except Exception:
                if anno == int: return int(value)
                elif anno == float: return float(value)
                elif anno == bool: return value.lower() in ('true', '1', 'yes')
                return value
        return value
    
    # Try FastHTML's _find_p for other parameters (form data, path params, etc.)
    result = None
    if hasattr(req, 'path_params') and hasattr(req, 'scope'):
        try:
            result = await _find_p(req, arg, p)
        except Exception:
            result = None
    
    # For POST requests, also check form data manually
    if result is None and hasattr(req, 'method') and req.method == 'POST':
        try:
            form_data = await parse_form(req)
            if hasattr(form_data, 'get') and form_data.get(arg) is not None:
                value = form_data.get(arg)
                # Apply type conversion if needed
                if anno != inspect.Parameter.empty:
                    try:
                        return _fix_anno(anno, value)
                    except Exception:
                        # Basic type conversion fallback
                        if anno == int:
                            return int(value)
                        elif anno == float:
                            return float(value)
                        elif anno == bool:
                            return value.lower() in ('true', '1', 'yes')
                        return value
                return value
        except Exception:
            pass
    
    # ONLY if no query param, no form data, and no _find_p result, check datastar payload (lowest priority)
    if result is None:
        # Check datastar payload as fallback
        if datastar_payload and arg in datastar_payload:
            value = datastar_payload[arg]
            # Apply type conversion if needed
            if anno != inspect.Parameter.empty:
                try:
                    return _fix_anno(anno, value)
                except Exception:
                    return value
            return value
    
    return result


async def _wrap_req_with_datastar(req: Request, params: Dict[str, inspect.Parameter], namespace: str = None):
    """
    Extended version of _wrap_req that supports Datastar parameters.
    
    Uses unified parameter extraction with proper priority:
    1. Query parameters (highest priority)
    2. Form data  
    3. Datastar payload (lowest priority)
    """
    # Extract Datastar payload using unified approach
    datastar_payload = await _extract_datastar_payload(req)
    
    # Handle namespace if specified
    if namespace and namespace in datastar_payload.raw_data:
        # Merge namespaced data into the top level while keeping the original structure
        namespaced_data = datastar_payload.get(namespace, {})
        merged_data = {**datastar_payload.raw_data, **namespaced_data}
        from ..core.events import DatastarPayload
        datastar_payload = DatastarPayload(merged_data)
    
    # Process all parameters with unified Datastar support
    result = []
    for arg, p in params.items():
        param_value = await _find_p_with_datastar(req, arg, p, datastar_payload)
        result.append(param_value)
    
    return result
