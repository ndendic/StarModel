import asyncio
import inspect
import json
import urllib.parse
import uuid
import typing

from datastar_py import SSE_HEADERS
from datastar_py import ServerSentEventGenerator as SSE
from fasthtml.common import *
from fasthtml.core import APIRouter, StreamingResponse
from monsterui.franken import *
from sqlmodel import Field, SQLModel

rt = APIRouter()

class ReactiveState(SQLModel):
    # id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # utility: send just-changed fields over SSE --------------------------- #
    def _diff_and_events(self, before: dict, after: dict):
        changed = {k: v for k, v in after.items() if before.get(k) != v}
        if changed:
            yield SSE.merge_signals(changed)
    
    def __ft__(self):
        return Div(
            H2(f"State : {self.__class__.__name__} ({self.id})", cls="mt-4"),
            *[Div(f"{k}: ",Span(data_text=f"${k}")) for k, v in self.model_dump().items()],
            data_signals=json.dumps(self.model_dump()))

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, member in inspect.getmembers(cls):
            if hasattr(member, '_faststate_event_config'):
                event_config = member._faststate_event_config
                original_method = member
                
                url_generator_static_method = _build_event_handler_and_url_generator(
                    cls,
                    original_method,
                    event_config
                )
                setattr(cls, name, url_generator_static_method)

    @classmethod
    def get(cls, req: Request, sess: dict = None, auth: str = None) -> 'ReactiveState':
        """
        Get state instance for this state class from the request context.
        
        Args:
            req: FastHTML request object
            sess: Session dictionary (auto-extracted if not provided)
            auth: Authentication string (auto-extracted if not provided)
            
        Returns:
            State instance for the given scope and context
            
        Example:
            my_state = MyState.get(req)
            user_profile = UserProfileState.get(req, sess, auth)
        """
        # Auto-extract session and auth if not provided
        if sess is None:
            sess = getattr(req, 'session', {})
        if auth is None:
            auth = req.scope.get("user") or sess.get("auth")
        
        # Use state registry resolution logic
        try:
            from .registry import state_registry
            if state_registry.is_state_type(cls):
                return state_registry.resolve_state_sync(cls, req, sess, auth)
        except (ImportError, AttributeError):
            pass
        
        # Fallback: create new instance (for backward compatibility)
        return cls()


async def _get_state(request: Request, cls: type[ReactiveState], id: str | None = None) -> ReactiveState:
    """
    Get state instance for the given request. Uses state registry when available,
    falls back to legacy behavior for backward compatibility.
    """
    # Try to use the state registry first if available
    try:
        from .registry import state_registry
        if state_registry.is_state_type(cls):
            # Extract session and auth from request for registry
            session = getattr(request, 'session', {})
            auth = session.get('auth', None)
            # auth = getattr(request, 'auth', None)  # May be set by beforeware
            return await state_registry.resolve_state(cls, request, session, auth)
    except (ImportError, AttributeError, KeyError):
        pass

VERBS = {"get", "post", "put", "patch", "delete"}

# ------------------------------------------------------------------ #
def _build_event_handler_and_url_generator(state_class: type['ReactiveState'], original_func, event_config: dict):
    # Resolve the route path: custom or default
    custom_path_from_config = event_config.get('custom_route_path')
    final_route_path: str

    if custom_path_from_config:
        final_route_path = custom_path_from_config
        if not final_route_path.startswith("/"):
            final_route_path = "/" + final_route_path
    else:
        final_route_path = "/" + original_func.__qualname__.replace(".", "/") # Default behavior

    method = event_config['method']
    selector = event_config['selector']
    merge_mode = event_config['merge_mode']

    class ParameterConversionError(ValueError):
        pass

    def _convert_single_param(raw_val, type_hint, p_name: str):
        expected_type_to_convert_to = None
        if type_hint is int: expected_type_to_convert_to = int
        elif type_hint is float: expected_type_to_convert_to = float
        elif type_hint is bool: expected_type_to_convert_to = bool

        if expected_type_to_convert_to:
            if isinstance(raw_val, str): # Value from query string, needs conversion
                if expected_type_to_convert_to is bool:
                    if raw_val.lower() in ('true', '1', 'yes', 'on'): return True
                    elif raw_val.lower() in ('false', '0', 'no', 'off'): return False
                    else: raise ParameterConversionError(f"Invalid boolean value for parameter '{p_name}': {raw_val}")
                else: # int or float from string
                    try: return expected_type_to_convert_to(raw_val)
                    except ValueError: raise ParameterConversionError(f"Invalid value for parameter '{p_name}': '{raw_val}'. Expected {expected_type_to_convert_to.__name__}.")
            elif isinstance(raw_val, expected_type_to_convert_to): # Value from JSON, already correct type
                return raw_val
            elif expected_type_to_convert_to is float and isinstance(raw_val, int): # Allow int for float (e.g. from JSON)
                return float(raw_val)
            else: # Mismatch between actual type (e.g. from JSON) and annotation
                raise ParameterConversionError(f"Incorrect type for parameter '{p_name}'. Expected {expected_type_to_convert_to.__name__}, got {type(raw_val).__name__}.")
        elif type_hint is str: # Explicitly string type hint
            return str(raw_val)
        else:
            if isinstance(raw_val, (str, int, float, bool)) or raw_val is None:
                return raw_val 
            return str(raw_val)

    async def _handler(request):
        state = await _get_state(request, state_class)
        before = state.model_dump()

        sig = inspect.signature(original_func)
        bound = {}
        datastar_payload = None
        datastar_json_str = request.query_params.get('datastar')
        if datastar_json_str:
            try:
                datastar_payload = json.loads(datastar_json_str)
            except json.JSONDecodeError:
                datastar_payload = None
                print(f"Warning: 'datastar' query parameter contained invalid JSON: {datastar_json_str}")

        for name, param in list(sig.parameters.items())[1:]:
            raw_value = request.query_params.get(name)

            if raw_value is None and datastar_payload and name in datastar_payload:
                raw_value = datastar_payload[name]
            
            if raw_value is not None:
                try:
                    actual_type_hint = typing.get_origin(param.annotation) or param.annotation
                    bound[name] = _convert_single_param(raw_value, actual_type_hint, name)
                except ParameterConversionError as e:
                    return P(str(e), cls="text-red-500 mt-4") # User wants P components for errors
            elif param.default is inspect.Parameter.empty: # raw_value is None, and no default value
                return P(f"Missing required parameter: '{name}'", cls="text-red-500 mt-4")
            else: # raw_value is None, but there is a default value
                bound[name] = param.default

        out = await original_func(state, **bound) if asyncio.iscoroutinefunction(original_func) else original_func(state, **bound)
        after = state.model_dump()
        
        # Broadcast state changes via SSE manager if available and state has changed
        state_changes = {k: v for k, v in after.items() if before.get(k) != v}
        if state_changes:
            try:
                from .registry import state_registry
                from .sse_manager import sse_manager
                from .registry import StateScope
                
                # Get state configuration if registered
                if state_registry.is_state_type(state_class):
                    config = state_registry._state_configs.get(state_class)
                    if config:
                        # Extract context for broadcasting
                        session = getattr(request, 'session', {})
                        auth = session.get('auth', None)
                        # auth = getattr(request, 'auth', None)
                        session_id = request.cookies.get('session_')[:100]
                        user_id = auth if isinstance(auth, str) else None
                        
                        # Determine record_id for RECORD scope
                        record_id = None
                        if config.scope == StateScope.RECORD:
                            record_id = getattr(state, 'id', None) or request.query_params.get('record_id')
                        
                        # Broadcast the changes
                        sse_manager.broadcast_state_change(
                            state_class_name=state_class.__name__,
                            state_changes=state_changes,
                            scope=config.scope,
                            session_id=session_id,
                            user_id=user_id,
                            record_id=record_id
                        )
            except (ImportError, AttributeError) as e:
                # SSE manager not available, continue without broadcasting
                print(f"Warning: SSE broadcasting not available: {e}")
                pass

        async def stream_response_content():
            for ev_data in state._diff_and_events(before, after):
                yield ev_data
            
            if out is not None:
                if hasattr(out, '__aiter__'): 
                    async for fragment in out:
                        yield SSE.merge_fragments([to_xml(fragment)], selector=selector, merge_mode=merge_mode)
                else:
                    fragments = []
                    if hasattr(out, '__iter__') and not isinstance(out, (str, FT)):
                        fragments = [to_xml(f) for f in out]
                    else: 
                        fragments = [to_xml(out)]
                    if fragments:
                        yield SSE.merge_fragments(fragments, selector=selector, merge_mode=merge_mode)

        return StreamingResponse(stream_response_content(),
                                 media_type="text/event-stream",
                                 headers=SSE_HEADERS)

    rt(final_route_path, methods=[method.upper()])(_handler)

    param_names = event_config['original_params']
    def _url_generator_for_method(*call_args, _method=method, **call_kwargs):
        qs_dict = {k: v for k, v in zip(param_names, call_args)}
        qs_dict.update(call_kwargs)
        qs = urllib.parse.urlencode(qs_dict)
        return f"@{_method}('{final_route_path}?{qs}')" if qs else f"@{_method}('{final_route_path}')"

    return staticmethod(_url_generator_for_method)

def event(
    _func_or_pos_path: typing.Union[callable, str, None] = None,
    *,
    method: str = "get",
    selector: str | None = None,
    merge_mode: str = "morph",
    path: str | None = None  # Explicit keyword for path
):
    def _configure_and_get_decorator(actual_custom_path_val: str | None):
        def _decorator(func_to_decorate):
            sig_params = list(inspect.signature(func_to_decorate).parameters.keys())
            if not sig_params or sig_params[0] != 'self':
                 raise TypeError(
                     f"@event decorator expects '{func_to_decorate.__qualname__}' to be an instance method "
                     f"with 'self' as its first parameter. Found parameters: {sig_params}"
                )

            method_lower = method.lower()
            if method_lower not in VERBS:
                raise ValueError(f"Unsupported HTTP verb: {method_lower!r}")

            func_to_decorate._faststate_event_config = {
                "method": method_lower,
                "selector": selector,
                "merge_mode": merge_mode,
                "original_params": sig_params[1:],
                "custom_route_path": actual_custom_path_val
            }
            return func_to_decorate
        return _decorator

    effective_custom_path: str | None = None

    if isinstance(_func_or_pos_path, str):
        # Called as @event("custom/path", ...)
        if path is not None and path != _func_or_pos_path:
            raise ValueError(
                f"Path specified both positionally ('{_func_or_pos_path}') and as a keyword argument ('{path}'). Please use only one."
            )
        effective_custom_path = _func_or_pos_path
        return _configure_and_get_decorator(effective_custom_path) # Returns the _decorator
    
    elif callable(_func_or_pos_path):        
        if path is not None:
             raise ValueError(
                f"Cannot use keyword 'path' argument ('{path}') when @event is applied directly without parentheses "
                f"and a positional path is not given. Did you mean @event(path='{path}')?"
            )
        # effective_custom_path remains None, path will be derived from func name by the builder
        decorator_instance = _configure_and_get_decorator(None) 
        return decorator_instance(_func_or_pos_path) # Apply decorator immediately
    
    else: # _func_or_pos_path is None (e.g., @event() or @event(method="post", path="kw/path"))
        effective_custom_path = path # Use keyword path if provided, else None
        return _configure_and_get_decorator(effective_custom_path) # Returns the _decorator


# SSE Connection Management Functions
# ========================================

async def create_sse_connection_handler(request: Request):
    """
    Create an SSE connection for real-time state updates.
    
    This endpoint allows clients to establish persistent SSE connections
    to receive broadcast state updates based on their subscriptions.
    """
    try:
        from .sse_manager import sse_manager
        
        # Extract connection parameters
        query_params = request.query_params
        session = getattr(request, 'session', {})
        auth = request.get('auth', None)
        
        session_id = request.cookies.get('session_')[:100] or str(uuid.uuid4())
        user_id = auth if isinstance(auth, str) else None
        subscribed_states = query_params.get('states', '').split(',') if query_params.get('states') else []
        
        # Clean up state names
        subscribed_states = [s.strip() for s in subscribed_states if s.strip()]
        
        # Create SSE connection
        connection = sse_manager.create_connection(
            session_id=session_id,
            user_id=user_id,
            subscribed_states=subscribed_states
        )
        
        # Return SSE stream
        return StreamingResponse(
            sse_manager.get_sse_stream(connection.connection_id),
            media_type="text/event-stream",
            headers=SSE_HEADERS
        )
        
    except ImportError:
        # SSE manager not available, return empty stream
        async def empty_stream():
            yield SSE.create_event(data={"error": "SSE manager not available"})
        
        return StreamingResponse(
            empty_stream(),
            media_type="text/event-stream",
            headers=SSE_HEADERS
        )


# Register the SSE connection endpoint
rt("/faststate/sse", methods=["GET"])(create_sse_connection_handler)
