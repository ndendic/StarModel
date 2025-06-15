import inspect
import json
import urllib.parse
from typing import Any, Dict

from datastar_py import SSE_HEADERS
from datastar_py import ServerSentEventGenerator as SSE
from fasthtml.common import *
from fasthtml.core import APIRouter, StreamingResponse, _find_p, parse_form

rt = APIRouter()

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

def datastar_from_queryParams(request: Request) -> DatastarPayload:
    """Synchronous version - Extract Datastar payload from request (query params only)."""
    datastar_payload = None
    
    try:
        # Only try getting datastar from query params in sync version
        datastar_json_str = request.query_params.get('datastar')
        if datastar_json_str:
            datastar_payload = json.loads(datastar_json_str)
    except Exception:
        datastar_payload = None
    
    return DatastarPayload(datastar_payload)

async def _extract_datastar_payload(request: Request) -> DatastarPayload:
    """Extract Datastar payload from request."""
    datastar_payload = None
    
    try:
        # Try getting datastar from query params first
        datastar_json_str = request.query_params.get('datastar')
        if datastar_json_str:
            datastar_payload = json.loads(datastar_json_str)
        else:
            # Try getting from JSON body
            try:
                datastar_payload = await request.json()
            except Exception:
                # Try getting from form data
                form_data = await parse_form(request)
                if hasattr(form_data, 'get'):
                    datastar_json_str = form_data.get('datastar')
                    if datastar_json_str:
                        datastar_payload = json.loads(datastar_json_str)
    except Exception:
        datastar_payload = None
    
    return DatastarPayload(datastar_payload)

async def _find_p_with_datastar(req: Request, arg: str, p, datastar_payload: DatastarPayload):
    """Extended version of FastHTML's _find_p that also supports Datastar parameters."""
    anno = p.annotation
        
    try:
        result = await _find_p(req, arg, p) # Use FastHTML's original _find_p function
    except Exception:
        result = None

    if result is None:
        # Handle Datastar payload injection
        if isinstance(anno, type) and issubclass(anno, DatastarPayload):
            return datastar_payload
        if anno is DatastarPayload:
            return datastar_payload
        if arg.lower() == 'datastar' and anno is inspect.Parameter.empty:
            return datastar_payload
                
        if datastar_payload and arg in datastar_payload:
            value = datastar_payload[arg]
            # Apply type conversion if needed
            if anno != inspect.Parameter.empty:
                from fasthtml.core import _fix_anno
                try:
                    return _fix_anno(anno, value)
                except Exception:
                    return value
            return value
    
    return result

async def _wrap_req_with_datastar(req: Request, params: Dict[str, inspect.Parameter], namespace: str = None):
    """Extended version of _wrap_req that supports Datastar parameters."""
    # Extract Datastar payload first
    datastar_payload = await _extract_datastar_payload(req)
    if namespace and namespace in datastar_payload.raw_data:
    # Merge namespaced data into the top level while keeping the original structure
        namespaced_data = datastar_payload.get(namespace, {})
        merged_data = {**datastar_payload.raw_data, **namespaced_data}
        datastar_payload = DatastarPayload(merged_data)
    
    # Process all parameters with Datastar support
    result = []
    for arg, p in params.items():
        param_value = await _find_p_with_datastar(req, arg, p, datastar_payload)
        result.append(param_value)
    
    return result

def _register_event_route(state_cls, method, config):
    """Register an event method as a FastHTML route using FastHTML's parameter injection system."""
    # Generate route path
    path = config.get('path') or f"/{state_cls.__name__}/{method.__name__}"
    methods = [config.get('method', 'get').upper()]
    selector = config.get('selector')
    merge_mode = config.get('merge_mode', 'morph')
    name = config.get('name')
    include_in_schema = config.get('include_in_schema', True)
    body_wrap = config.get('body_wrap')
    
    # Get method signature for FastHTML parameter injection
    sig = inspect.signature(method)
    
    # Create the route handler using FastHTML patterns
    async def event_handler(request: Request):
        # Get state instance (this handles session, auth extraction internally)
        state = state_cls.get(request)
        
        # Use enhanced parameter resolution system with Datastar support
        # This handles all parameter extraction including Datastar payload
        namespace = state.namespace if state.use_namespace else None
        wrapped_params = await _wrap_req_with_datastar(request, sig.parameters, namespace=namespace)
        
        # Call the method with resolved parameters (skip 'self' which is index 0)
        # The state instance replaces 'self', so we use state + params[1:]
        method_params = [state] + wrapped_params[1:]
        
        # Check if method is async before calling _handle
        if inspect.iscoroutinefunction(method):
            result = await method(*method_params)
        else:
            result = method(*method_params)
        
        # Auto-persist state changes if configured
        if state.auto_persist and not state.store.startswith("client_"):
            state.save()
        
        # Handle async generators and regular returns
        async def sse_stream():            
            # Always send current state signals first
            yield SSE.merge_signals(state.signals)
            
            if hasattr(result, '__aiter__'):  # Async generator
                async for item in result:
                    # Auto-persist state changes after each yield if configured
                    if state.auto_persist and not state.store.startswith("client_"):
                        state.save()
                    
                    # Send updated state after each yield
                    yield SSE.merge_signals(state.signals)
                    if item and (hasattr(item, '__ft__') or isinstance(item, FT)):  # FT component
                        fragments = [to_xml(item)]
                        if selector:
                            for fragment in fragments:
                                yield SSE.merge_fragments(fragment, selector=selector, merge_mode=merge_mode)
                        else:
                            for fragment in fragments:
                                yield SSE.merge_fragments(fragment, merge_mode=merge_mode)
            else:  # Regular return or None
                if result and (hasattr(result, '__ft__') or isinstance(result, FT)):  # FT component
                    fragments = [to_xml(result)]
                    if selector:
                        for fragment in fragments:
                            yield SSE.merge_fragments(fragment, selector=selector, merge_mode=merge_mode) 
                    else:
                        for fragment in fragments:
                            yield SSE.merge_fragments(fragment, merge_mode=merge_mode)
        
        return StreamingResponse(sse_stream(), media_type="text/event-stream", headers=SSE_HEADERS) 
    
    # Register with APIRouter following FastHTML pattern
    rt(path, methods=methods, name=name, include_in_schema=include_in_schema, body_wrap=body_wrap)(event_handler)

def _add_url_generator(state_cls, method_name, method, config):
    """Add URL generator static method to the state class with FastHTML compatibility."""
    # Generate route path (same logic as in _register_event_route)
    path = config.get('path') or f"/{state_cls.__name__}/{method_name}"
    http_method = config.get('method', 'get')
    
    # Get parameter names from method signature, filtering out FastHTML special params
    sig = inspect.signature(method)
    param_names = []
    special_params = {'session', 'auth', 'request', 'htmx', 'scope', 'app', 'datastar'}
    
    for name, param in list(sig.parameters.items())[1:]:  # Skip 'self'
        # Skip FastHTML special parameters that get auto-injected
        if name.lower() not in special_params:
            # Also skip if annotation indicates it's a special FastHTML type
            anno = param.annotation
            if anno != inspect.Parameter.empty:
                if hasattr(anno, '__name__'):
                    if anno.__name__ in ('Request', 'HtmxHeaders', 'Starlette', 'DatastarPayload'):
                        continue
            param_names.append(name)
    
    def url_generator(*call_args, **call_kwargs):
        # Build query parameters from args and kwargs
        params = {}
        
        # Add positional arguments
        for i, arg in enumerate(call_args):
            if i < len(param_names):
                params[param_names[i]] = arg
        
        # Add keyword arguments (filter out None values)
        params.update({k: v for k, v in call_kwargs.items() if v is not None})
        
        # Build query string
        if params:
            query_string = urllib.parse.urlencode(params, doseq=True)
            return f"@{http_method}('{path}?{query_string}')"
        else:
            return f"@{http_method}('{path}')"
    
    # Set the URL generator as a static method on the class
    # We need to preserve the original method, so we add the URL generator as an attribute
    url_generator_method = staticmethod(url_generator)
    
    # Store the URL generator on the class, preserving the original method
    if not hasattr(state_cls, '_url_generators'):
        state_cls._url_generators = {}
    state_cls._url_generators[method_name] = url_generator_method
    
    # Also set it as a class attribute so it can be accessed as ClassName.method_name()
    setattr(state_cls, method_name, url_generator_method)

def event(path=None, *, method="get", selector=None, merge_mode="morph", name=None, include_in_schema=True, body_wrap=None):
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
            'merge_mode': merge_mode,
            'name': name,
            'include_in_schema': include_in_schema,
            'body_wrap': body_wrap
        }
        return func
    
    if callable(path):  # Used as @event without parentheses
        func = path
        func._event_config = {'path': None, 'method': 'get', 'selector': None, 'merge_mode': 'morph', 'name': None, 'include_in_schema': True, 'body_wrap': None}
        return func
    
    return decorator