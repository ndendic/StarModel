import inspect
import asyncio
import json
import uuid
import urllib.parse

from datastar_py import SSE_HEADERS
from datastar_py import ServerSentEventGenerator as SSE
from fasthtml.common import *
from fasthtml.core import APIRouter, StreamingResponse
from pydantic import BaseModel, Field

datastar_script = Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0-beta.11/bundles/datastar.js", type="module")

rt = APIRouter()

def _register_event_route(state_cls, method, config):
    """Register an event method as a FastHTML route using APIRouter pattern."""
    # Generate route path
    path = config.get('path') or f"/{state_cls.__name__}/{method.__name__}"
    methods = [config.get('method', 'get').upper()]
    selector = config.get('selector')
    merge_mode = config.get('merge_mode', 'morph')
    
    # Create the route handler
    async def event_handler(request: Request):
        # Get state instance        
        state = state_cls.get(request)        
        # Extract parameters from request
        params = {}
        sig = inspect.signature(method)
        datastar_payload = None
        
        try:
            datastar_json_str = request.query_params.get('datastar')
            if datastar_json_str:
                datastar_payload = json.loads(datastar_json_str)
            else:
                datastar_payload = await request.json()
        except:
            datastar_payload = None
        
        for param_name, param in list(sig.parameters.items())[1:]:  # Skip 'self'
            # Try query params first, then JSON body
            value = request.query_params.get(param_name)
            if value is None and datastar_payload and param_name in datastar_payload:
                value = datastar_payload[param_name]                
            
            if value is not None:
                # Simple type conversion
                if param.annotation == int:
                    value = int(value)
                elif param.annotation == float:
                    value = float(value)
                elif param.annotation == bool:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                
                params[param_name] = value
            elif param.default is inspect.Parameter.empty:
                raise ValueError(f"Missing required parameter: {param_name}")
            else:
                params[param_name] = param.default
        
        # Call the method
        result = method(state, **params)
        
        # Handle async generators and regular returns
        async def sse_stream():            
            # Handle method result
            yield SSE.merge_signals(state.model_dump())
            if hasattr(result, '__aiter__'):  # Async generator
                async for item in result:
                    yield SSE.merge_signals(state.model_dump())
                    if item and (hasattr(item, '__ft__') or isinstance(item, FT)):  # FT component
                        fragments = [to_xml(item)]
                        if selector:
                            yield SSE.merge_fragments(fragments, selector=selector, merge_mode=merge_mode)
                        else:
                            yield SSE.merge_fragments(fragments, merge_mode=merge_mode)
            else:  # Regular return or None
                yield SSE.merge_signals(state.model_dump())
                if result and (hasattr(result, '__ft__') or isinstance(result, FT)):  # FT component
                    fragments = [to_xml(result)]
                    if selector:
                        yield SSE.merge_fragments(fragments, selector=selector, merge_mode=merge_mode)
                    else:
                        yield SSE.merge_fragments(fragments, merge_mode=merge_mode)
        
        return StreamingResponse(sse_stream(), media_type="text/event-stream", headers=SSE_HEADERS)
    
    # Register with APIRouter following FastHTML pattern
    rt(path, methods=methods)(event_handler)


def _add_url_generator(state_cls, method_name, method, config):
    """Add URL generator static method to the state class."""
    # Generate route path (same logic as in _register_event_route)
    path = config.get('path') or f"/{state_cls.__name__}/{method_name}"
    http_method = config.get('method', 'get')
    
    # Get parameter names from method signature
    sig = inspect.signature(method)
    param_names = list(sig.parameters.keys())[1:]  # Skip 'self'
    
    def url_generator(*call_args, **call_kwargs):
        # Build query parameters from args and kwargs
        params = {}
        
        # Add positional arguments
        for i, arg in enumerate(call_args):
            if i < len(param_names):
                params[param_names[i]] = arg
        
        # Add keyword arguments
        params.update(call_kwargs)
        
        # Build query string
        if params:
            query_string = urllib.parse.urlencode(params)
            return f"@{http_method}('{path}?{query_string}')"
        else:
            return f"@{http_method}('{path}')"
    
    # Set the URL generator as a static method on the class
    setattr(state_cls, method_name, staticmethod(url_generator))


def event(path=None, *, method="get", selector=None, merge_mode="morph"):
    """
    Simplified event decorator for State methods.
    
    Args:
        path: Custom route path (optional, defaults to /{ClassName}/{method_name})
        method: HTTP method (default: "get")
        selector: Datastar selector for fragment updates (optional)
        merge_mode: Datastar merge mode (default: "morph")
    """
    def decorator(func):
        # Store config on the function
        func._event_config = {
            'path': path,
            'method': method,
            'selector': selector,
            'merge_mode': merge_mode
        }
        return func
    
    if callable(path):  # Used as @event without parentheses
        func = path
        func._event_config = {'path': None, 'method': 'get', 'selector': None, 'merge_mode': 'morph'}
        return func
    
    return decorator


class State(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Configuration (excluded from model_dump by Pydantic underscore convention)
    _config = None  # Will use default StateConfig if not set
    
    

    def LiveDiv(self, heartbeat: float = 0):
        return Div({"data-on-load": self.live(heartbeat)}, id=f"{self.__class__.__name__}")

    def SignalsDiv(self):
        return Div({"data-signals": json.dumps(self.model_dump())}, id=f"{self.__class__.__name__}"),

    
    @event
    async def live(self, heartbeat: float = 0):
        while True:
            yield self.model_dump()
            await asyncio.sleep(heartbeat)

    
    def __ft__(self):
        return self.SignalsDiv()    
    
    @classmethod
    def _get_config(cls):
        """Get the effective StateConfig for this class."""
        from .registry import StateConfig
        
        # Check if this class (not parent) defines _config
        config_attr = getattr(cls, '_config', None)
        
        # Check if this is a ModelPrivateAttr with a default, or a direct value
        if hasattr(config_attr, 'default') and config_attr.default is not None:
            config = config_attr.default
        elif config_attr is not None and not hasattr(config_attr, 'default'):
            config = config_attr
        else:
            # Check if this class is the base State class or a subclass without explicit config
            if cls.__name__ == 'State' or '_config' not in cls.__private_attributes__:
                config = StateConfig()
            else:
                # This should not happen, but fallback to default
                config = StateConfig()
        
        return config

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register event-decorated methods as routes and add URL generators
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(method, '_event_config'):
                # Register the route
                _register_event_route(cls, method, method._event_config)
                # Add URL generator static method
                _add_url_generator(cls, name, method, method._event_config)
    

    @classmethod
    def get(cls, req: Request, sess: dict = None, auth: str = None) -> 'State':
        """Get state instance for this state class from the request context."""
        # Auto-extract session and auth if not provided
        if sess is None:
            sess = req.get('session', None)
        if auth is None:
            auth = req.get("auth", None) if req else None
            if not auth and sess:
                auth = sess.get("user", None)
        
        # Import needed components
        try:
            from .registry import state_registry
            
            # Auto-register the state class if not already registered
            if not state_registry.is_state_type(cls):
                # Get effective config for this class
                config = cls._get_config()
                
                # Register the state
                state_registry.register(cls, config)
            
            # Use state registry resolution logic
            return state_registry.resolve_state_sync(cls, req, sess, auth)
            
        except (ImportError, AttributeError, Exception) as e:
            print(f"Error getting state: {e}")
            # Fallback: create new instance (for backward compatibility)
            return cls()