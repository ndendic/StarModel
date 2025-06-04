# FastState Core Components

This document provides detailed technical documentation for each core component of the FastState system.

## Table of Contents

1. [State Base Class](#state-base-class)
2. [State Registry System](#state-registry-system)
3. [Auto-Registration System](#auto-registration-system)
4. [Event Decorator System](#event-decorator-system)
5. [Configuration System](#configuration-system)
6. [SSE Response Generation](#sse-response-generation)

---

## State Base Class

**Location**: `src/faststate/state.py`

The `State` class is the foundation of the FastState system, providing reactive state management with automatic SSE generation and auto-registration.

### Class Definition

```python
class State(BaseModel):
    """
    Base class for reactive state management with automatic SSE generation.
    
    Inherits from Pydantic BaseModel to provide:
    - Data validation and type safety
    - JSON serialization for SSE responses
    - Model configuration and field management
    - Automatic configuration handling
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Configuration (excluded from model_dump by Pydantic underscore convention)
    _config = None  # Will use default StateConfig if not set
```

### Key Features

#### 1. Automatic ID Generation
Every state instance gets a unique UUID for identification:
- **Purpose**: Track state instances across requests
- **Type**: String UUID4
- **Usage**: Used in state registry caching and client identification

#### 2. Pydantic BaseModel Integration
Inherits all BaseModel capabilities:
- **Validation**: Automatic type checking and validation
- **Serialization**: JSON serialization for SSE responses
- **Configuration**: Field management and model configuration

#### 3. Auto-Registration System
States automatically register themselves on first access:
```python
@classmethod
def get(cls, req: Request, sess: dict = None, auth: str = None) -> 'State':
    """Get state instance for this state class from the request context."""
    # Auto-registration happens here on first access
    config = cls._get_config()
    if not state_registry.is_state_type(cls):
        state_registry.register(cls, config)
    return state_registry.resolve_state_sync(cls, req, sess, auth)
```

#### 4. Configuration Resolution
Smart configuration handling with defaults:
```python
@classmethod
def _get_config(cls):
    """Get the effective StateConfig for this class."""
    from .registry import StateConfig
    
    # Check if this class (not parent) defines _config
    config_attr = getattr(cls, '_config', None)
    
    if hasattr(config_attr, 'default') and config_attr.default is not None:
        config = config_attr.default
    elif config_attr is not None and not hasattr(config_attr, 'default'):
        config = config_attr
    else:
        # Use default StateConfig for classes without explicit config
        config = StateConfig()
    
    return config
```

#### 5. Event Method Registration
Automatic route generation for `@event` decorated methods:
```python
def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    # Register event-decorated methods as routes and add URL generators
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if hasattr(method, '_event_config'):
            # Register the route
            _register_event_route(cls, method, method._event_config)
            # Add URL generator static method
            _add_url_generator(cls, name, method, method._event_config)
```

#### 6. UI Rendering Support
Built-in methods for FastHTML integration:
```python
def __ft__(self):
    return self.SignalsDiv()

def SignalsDiv(self):
    return Div({"data-signals": json.dumps(self.model_dump())}, id=f"{self.__class__.__name__}")

def LiveDiv(self, heartbeat: float = 0):
    return Div({"data-on-load": self.live(heartbeat)}, id=f"{self.__class__.__name__}")
```

---

## State Registry System

**Location**: `src/faststate/registry.py`

The registry system manages state instances with different scopes and configurations, providing automatic caching and persistence integration.

### StateScope Enum

```python
class StateScope(StrEnum):
    """Enumeration of different state scopes supported by FastState."""
    GLOBAL = "global"        # Shared across all users
    SESSION = "session"      # Per user session (current default)
    USER = "user"           # Per authenticated user across sessions
    COMPONENT = "component"  # Per component instance
    RECORD = "record"       # Tied to specific database record
```

### StateConfig Class

```python
class StateConfig(BaseModel):
    """Configuration for a state class defining its scope and persistence."""
    scope: StateScope = StateScope.SESSION
    ttl: Optional[int] = None  # Time to live in seconds
    auto_persist: bool = False
    persistence_backend: Optional[str] = None  # Name of persistence backend to use
```

### Registry Operations

#### State Registration
```python
def register(self, state_cls: Type['State'], config: StateConfig):
    """Register a state class for automatic dependency injection."""
    self._state_configs[state_cls] = config
```

#### State Resolution
```python
def resolve_state_sync(self, state_cls: Type, req: Request, sess: dict, auth: Optional[str] = None) -> 'State':
    """Resolve state instance based on registered configuration (synchronous version)."""
    config = self._state_configs[state_cls]
    
    # Generate state key based on scope
    state_key = self._generate_state_key(state_cls, config, req, sess, auth)
    
    # Return cached instance if available
    if state_key in self._state_instances:
        return self._state_instances[state_key]
    
    # Try to load from persistence if enabled
    state = None
    if config.auto_persist and config.persistence_backend:
        state = self._load_from_persistence_sync(state_cls, state_key, config)

    # Create new instance if not found in persistence
    if state is None:
        state = self._create_state_instance(state_cls, config, req, sess, auth)
    
    # Cache and optionally persist the instance
    self._state_instances[state_key] = state
    
    if config.auto_persist and config.persistence_backend:
        self._save_to_persistence_sync(state, state_key, config)
        
    return state
```

---

## Auto-Registration System

The auto-registration system eliminates the need for manual `state_registry.register()` calls by automatically registering states on first access.

### How It Works

1. **Class-Level Configuration**: States define configuration using `_config` attribute
2. **Smart Defaults**: States without `_config` get SESSION scope with no persistence
3. **First Access Registration**: Registration happens automatically when `.get()` is called
4. **Configuration Resolution**: Uses `_get_config()` to handle both explicit and default configurations

### Configuration Examples

```python
# Simple state with defaults (SESSION scope, no persistence)
class MyState(State):
    myInt: int = 0
    myStr: str = "Hello"
    # No _config needed - gets defaults automatically

# Advanced state with explicit configuration
class CounterState(State):
    count: int = 0
    
    _config = StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="database",
        ttl=3600
    )
```

### Benefits

- **Zero Setup**: No manual registration required
- **Type Safety**: Configuration validated by StateConfig dataclass
- **Smart Defaults**: Works out-of-the-box for simple use cases
- **Flexible**: Full configuration available when needed

---

## Event Decorator System

**Location**: `src/faststate/state.py` (functions: `event`, `_register_event_route`, `_add_url_generator`)

The event system provides automatic HTTP route generation and URL method creation for Datastar integration.

### Event Decorator

```python
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
```

### Route Registration

Routes are automatically registered during class creation:

```python
def _register_event_route(state_cls, method, config):
    """Register an event method as a FastHTML route using APIRouter pattern."""
    # Generate route path
    path = config.get('path') or f"/{state_cls.__name__}/{method.__name__}"
    methods = [config.get('method', 'get').upper()]
    selector = config.get('selector')
    merge_mode = config.get('merge_mode', 'morph')
    
    # Create the route handler with SSE streaming
    async def event_handler(request: Request):
        state = state_cls.get(request)
        # Extract parameters, call method, return SSE stream
        # ... (parameter extraction and SSE response logic)
    
    # Register with APIRouter
    rt(path, methods=methods)(event_handler)
```

### URL Generator Creation

Automatic static methods for Datastar attributes:

```python
def _add_url_generator(state_cls, method_name, method, config):
    """Add URL generator static method to the state class."""
    path = config.get('path') or f"/{state_cls.__name__}/{method_name}"
    http_method = config.get('method', 'get')
    
    def url_generator(*call_args, **call_kwargs):
        # Build query parameters from args and kwargs
        params = {}
        # ... (parameter building logic)
        
        if params:
            query_string = urllib.parse.urlencode(params)
            return f"@{http_method}('{path}?{query_string}')"
        else:
            return f"@{http_method}('{path}')"
    
    # Set as static method on the class
    setattr(state_cls, method_name, staticmethod(url_generator))
```

---

## Configuration System

The configuration system provides a unified approach to state configuration with smart defaults and explicit configuration options.

### Default Configuration

States without explicit `_config` automatically get:
- **Scope**: `StateScope.SESSION`
- **Auto-persist**: `False`
- **Persistence backend**: `None`
- **TTL**: `None`

### Explicit Configuration

States can define explicit configuration using StateConfig:

```python
class AdvancedState(State):
    data: dict = {}
    
    _config = StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="database",
        ttl=3600
    )
```

### Configuration Resolution Logic

The `_get_config()` method handles configuration resolution:

1. **Check for explicit config**: Look for `_config` attribute on the class
2. **Handle Pydantic fields**: Extract default value from ModelPrivateAttr if present
3. **Return direct value**: If config is a direct StateConfig instance
4. **Use defaults**: Create default StateConfig if no explicit config found

---

## SSE Response Generation

**Location**: `src/faststate/state.py` (within `_register_event_route`)

The SSE system provides real-time state synchronization using Server-Sent Events.

### SSE Stream Generation

```python
async def sse_stream():
    # Always send current state
    yield SSE.merge_signals(state.model_dump())
    
    if hasattr(result, '__aiter__'):  # Async generator
        async for item in result:
            yield SSE.merge_signals(state.model_dump())
            if item and (hasattr(item, '__ft__') or isinstance(item, FT)):
                fragments = [to_xml(item)]
                if selector:
                    yield SSE.merge_fragments(fragments, selector=selector, merge_mode=merge_mode)
                else:
                    yield SSE.merge_fragments(fragments, merge_mode=merge_mode)
    else:  # Regular return or None
        yield SSE.merge_signals(state.model_dump())
        if result and (hasattr(result, '__ft__') or isinstance(result, FT)):
            fragments = [to_xml(result)]
            if selector:
                yield SSE.merge_fragments(fragments, selector=selector, merge_mode=merge_mode)
            else:
                yield SSE.merge_fragments(fragments, merge_mode=merge_mode)

return StreamingResponse(sse_stream(), media_type="text/event-stream", headers=SSE_HEADERS)
```

### Key Features

1. **Automatic State Sync**: Always sends `merge_signals` with current state
2. **Fragment Updates**: Conditionally sends `merge_fragments` for FastHTML components
3. **Streaming Support**: Handles async generators for real-time streaming
4. **Merge Modes**: Supports different Datastar merge modes (morph, inner, outer, append, prepend)
5. **Selector Support**: Optional CSS selectors for targeted DOM updates

### Integration with Datastar

The SSE responses integrate seamlessly with Datastar on the client side:

- **merge_signals**: Updates bound data attributes (`data-text="$count"`)
- **merge_fragments**: Updates DOM fragments at specified selectors
- **Real-time**: Live updates without page refreshes
- **Bi-directional**: Client actions trigger server state changes, server changes update client UI