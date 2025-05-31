# FastState Core Components

This document provides detailed technical documentation for each core component of the FastState system.

## Table of Contents

1. [ReactiveState Base Class](#reactivestate-base-class)
2. [State Registry System](#state-registry-system)
3. [FastHTML Integration Layer](#fasthtml-integration-layer)
4. [Event Decorator System](#event-decorator-system)
5. [SSE Response Generation](#sse-response-generation)

---

## ReactiveState Base Class

**Location**: `src/faststate/state.py`

The `ReactiveState` class is the foundation of the FastState system, providing reactive state management with automatic SSE generation.

### Class Definition

```python
class ReactiveState(SQLModel):
    """
    Base class for reactive state management with automatic SSE generation.
    
    Inherits from SQLModel to provide:
    - Pydantic data validation
    - Type safety with Python type hints
    - Optional database persistence via SQLAlchemy
    - JSON serialization for SSE responses
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
```

### Key Features

#### 1. Automatic ID Generation
Every state instance gets a unique UUID for identification:
- **Purpose**: Track state instances across requests
- **Type**: String UUID4
- **Usage**: Used in state registry caching and client identification

#### 2. SQLModel Integration
Inherits all SQLModel capabilities:
- **Validation**: Automatic type checking and validation
- **Serialization**: JSON serialization for SSE responses
- **Database**: Optional SQLAlchemy table creation
- **Type Safety**: Full mypy/IDE support

#### 3. Event Registration
The `@event` decorator automatically registers methods as HTTP endpoints:

```python
class MyState(ReactiveState):
    count: int = 0
    
    @event  # Creates /MyState/increment endpoint
    def increment(self, amount: int):
        self.count += amount
```

#### 4. SSE Response Generation
The `_diff_and_events` method creates SSE responses:

```python
def _diff_and_events(self, old_state: dict, new_state: dict) -> Any:
    """
    Generate SSE response with state changes.
    
    Args:
        old_state: Previous state as dict
        new_state: Current state as dict
        
    Returns:
        SSE response with datastar-merge-signals event
    """
    changes = {}
    for key, new_value in new_state.items():
        if key not in old_state or old_state[key] != new_value:
            changes[key] = new_value
    
    if changes:
        sse_data = f"event: datastar-merge-signals\ndata: {json.dumps(changes)}\n\n"
        return Response(content=sse_data, media_type="text/plain")
    
    return Response(content="", media_type="text/plain")
```

#### 5. HTML Rendering
The `__ft__` method enables direct use in FastHTML templates:

```python
def __ft__(self):
    """FastHTML component rendering"""
    return Div(
        H3("State Values", cls="text-xl font-bold mb-4"),
        Div("Count: ", Span(data_text="$count"), cls="mb-2"),
        # ... more UI elements
    )
```

### Internal Implementation Details

#### State Capture and Diffing
```python
@event
def my_event(self, param: str):
    # 1. Capture old state
    old_state = self.model_dump()
    
    # 2. Perform mutations
    self.some_property = param
    
    # 3. Capture new state
    new_state = self.model_dump()
    
    # 4. Generate SSE response with diffs
    return self._diff_and_events(old_state, new_state)
```

#### Method Registration Process
When a class is defined with `@event` decorated methods:
1. **Route Creation**: FastHTML route created at `/ClassName/method_name`
2. **Parameter Mapping**: Method parameters mapped to HTTP request parameters
3. **State Retrieval**: Current state instance retrieved from registry
4. **Method Execution**: Decorated method called with request parameters
5. **SSE Generation**: Automatic diff calculation and SSE response

---

## State Registry System

**Location**: `src/faststate/registry.py`

The registry system manages state instances, configurations, and scope-based resolution.

### StateScope Enumeration

```python
class StateScope(Enum):
    """Enumeration of different state scopes supported by FastState."""
    GLOBAL = "global"        # Shared across all users
    SESSION = "session"      # Per user session (default)
    USER = "user"           # Per authenticated user across sessions
    COMPONENT = "component"  # Per component instance
    RECORD = "record"       # Tied to specific database record
```

### StateConfig Class

```python
@dataclass
class StateConfig:
    """Configuration for a state class defining its scope and persistence."""
    scope: StateScope = StateScope.SESSION
    ttl: Optional[int] = None  # Time to live in seconds
    auto_persist: bool = False
```

**Configuration Options**:
- **scope**: Determines state isolation and sharing behavior
- **ttl**: Automatic cleanup after specified seconds (None = no expiration)
- **auto_persist**: Automatically save state changes to database

### FastStateRegistry Class

The registry manages all state types and instances.

#### Core Data Structures

```python
class FastStateRegistry:
    def __init__(self):
        self._state_configs: Dict[Type, StateConfig] = {}
        self._state_instances: Dict[str, 'ReactiveState'] = {}
```

- **_state_configs**: Maps state classes to their configurations
- **_state_instances**: Caches state instances by hierarchical keys

#### State Registration

```python
def register(self, state_cls: Type['ReactiveState'], config: StateConfig):
    """Register a state class for automatic dependency injection."""
    self._state_configs[state_cls] = config
```

**Process**:
1. Store state class and configuration mapping
2. Validate configuration consistency
3. Enable type-based resolution in dependency injection

#### State Resolution

```python
def resolve_state(self, state_cls: Type, req: Request, sess: dict, auth: Optional[str] = None) -> 'ReactiveState':
    """Resolve state instance based on registered configuration."""
    config = self._state_configs[state_cls]
    
    # Generate hierarchical state key
    state_key = self._generate_state_key(state_cls, config, req, sess, auth)
    
    # Return cached instance if available
    if state_key in self._state_instances:
        return self._state_instances[state_key]
    
    # Create new instance
    state = self._create_state_instance(state_cls, config, req, sess, auth)
    self._state_instances[state_key] = state
    
    # Maintain compatibility with existing session storage
    if config.scope == StateScope.SESSION:
        sess[f"{state_cls.__name__}_id"] = state.id
        
    return state
```

#### Hierarchical Key Generation

```python
def _generate_state_key(self, state_cls: Type, config: StateConfig, 
                       req: Request, sess: dict, auth: Optional[str]) -> str:
    """Generate hierarchical state key based on scope."""
    class_name = state_cls.__name__
    
    match config.scope:
        case StateScope.SESSION:
            session_id = sess.get('session_id', id(sess))
            return f"session:{class_name}:{session_id}"
            
        case StateScope.USER:
            if not auth:
                raise ValueError(f"User-scoped state {class_name} requires authentication")
            return f"user:{class_name}:{auth}"
            
        case StateScope.GLOBAL:
            return f"global:{class_name}"
            
        case StateScope.COMPONENT:
            # Component scoped to specific UI component instance
            component_id = (req.query_params.get('component_id') or 
                          req.path_params.get('component_id') or
                          sess.get(f'{class_name}_component_id', str(uuid.uuid4())))
            return f"component:{class_name}:{component_id}"
            
        case StateScope.RECORD:
            # Record scoped to specific database record
            record_id = (req.query_params.get('record_id') or 
                       req.path_params.get('record_id') or
                       req.query_params.get('id') or
                       req.path_params.get('id'))
            if not record_id:
                raise ValueError(f"Record-scoped state {class_name} requires record_id parameter")
            return f"record:{class_name}:{record_id}"
```

**Key Pattern Benefits**:
- **Namespace Isolation**: Different scopes can't collide
- **Predictable Keys**: Easy debugging and monitoring
- **Hierarchical Structure**: Clear scope relationships
- **Parameter Integration**: Automatic extraction from requests

#### Instance Creation and Persistence

```python
def _create_state_instance(self, state_cls: Type, config: StateConfig,
                          req: Request, sess: dict, auth: Optional[str]) -> 'ReactiveState':
    """Create new state instance, optionally loading from persistence."""
    if config.scope == StateScope.RECORD:
        # For record-scoped states, try to load from database first
        record_id = (req.query_params.get('record_id') or 
                    req.path_params.get('record_id') or
                    req.query_params.get('id') or
                    req.path_params.get('id'))
        
        if config.auto_persist and record_id:
            existing_state = self._load_from_persistence(state_cls, record_id)
            if existing_state:
                return existing_state
    
    # Create new instance
    return state_cls()

def _load_from_persistence(self, state_cls: Type, record_id: str) -> Optional['ReactiveState']:
    """Load state from persistence layer."""
    # Future: Integrate with database/Redis/etc.
    # For now, return None to always create new instances
    return None
```

---

## FastHTML Integration Layer

**Location**: `src/faststate/fasthtml_integration.py`

This layer extends FastHTML's dependency injection system through monkey patching.

### Monkey Patch Implementation

#### Core Patch Function

```python
def patch_fasthtml_for_state_injection():
    """Extend FastHTML's parameter injection system to handle state types."""
    try:
        import fasthtml.core
        from fasthtml.core import FastHTML
        
        # Store original add_route method
        original_add_route = FastHTML.add_route
        
        def enhanced_add_route(self, *args, **kwargs):
            """Enhanced route addition that wraps handlers with state injection."""
            
            # Handle different call patterns from FastHTML
            if len(args) >= 2:
                path, endpoint = args[0], args[1]
                remaining_args = args[2:]
            elif len(args) == 1 and hasattr(args[0], '__call__'):
                # Called as add_route(route_object)
                return original_add_route(self, *args, **kwargs)
            else:
                # Unknown pattern, pass through
                return original_add_route(self, *args, **kwargs)
            
            # Inspect endpoint for state parameters
            if callable(endpoint):
                sig = inspect.signature(endpoint)
                state_params = []
                
                for param_name, param in sig.parameters.items():
                    if state_registry.is_state_type(param.annotation):
                        state_params.append((param_name, param.annotation))
                
                if state_params:
                    # Create wrapper that injects states
                    endpoint = create_state_injecting_wrapper(endpoint, state_params)
            
            # Call original add_route with enhanced endpoint
            return original_add_route(self, path, endpoint, *remaining_args, **kwargs)
        
        # Apply the patch
        FastHTML.add_route = enhanced_add_route
        return True
        
    except ImportError:
        return False
```

#### State Injection Wrapper

```python
def create_state_injecting_wrapper(endpoint, state_params):
    """Create wrapper function that injects state instances."""
    
    @wraps(endpoint)
    def state_injecting_wrapper(*args, **kwargs):
        # Extract special FastHTML parameters
        req = kwargs.get('req') or kwargs.get('request')
        sess = kwargs.get('sess') or kwargs.get('session') or {}
        auth = kwargs.get('auth')
        
        if not req:
            # Try to find request in args
            for arg in args:
                if isinstance(arg, Request):
                    req = arg
                    break
        
        if not req:
            raise ValueError("Request object not available for state injection")
        
        # Inject state instances
        for param_name, state_type in state_params:
            if param_name not in kwargs:
                state_instance = state_registry.resolve_state(state_type, req, sess, auth)
                kwargs[param_name] = state_instance
        
        # Call original function with injected states
        return endpoint(*args, **kwargs)
    
    return state_injecting_wrapper
```

#### Async/Sync Compatibility

The wrapper handles both synchronous and asynchronous route functions:

```python
if asyncio.iscoroutinefunction(endpoint):
    @wraps(endpoint)
    async def async_state_injecting_wrapper(*args, **kwargs):
        # ... state injection logic
        return await endpoint(*args, **kwargs)
    
    endpoint = async_state_injecting_wrapper
else:
    @wraps(endpoint)
    def sync_state_injecting_wrapper(*args, **kwargs):
        # ... state injection logic
        return endpoint(*args, **kwargs)
    
    endpoint = sync_state_injecting_wrapper
```

### Integration Initialization

```python
def initialize_faststate():
    """Initialize FastState integration with FastHTML."""
    print("Initializing FastState integration with FastHTML...")
    
    success = patch_fasthtml_for_state_injection()
    
    if success:
        print("🎉 FastState initialization complete!")
        print("State types will now be automatically injected into route functions.")
    else:
        print("❌ FastState initialization failed!")
        print("Manual state management will be required.")
    
    return success
```

### Type Detection

```python
def is_state_type(self, annotation: Any) -> bool:
    """Check if a type annotation represents a registered state type."""
    # Handle generic types like Optional[StateType]
    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        if args:
            annotation = args[0]  # Extract actual type from Optional[Type]
    
    return annotation in self._state_configs
```

---

## Event Decorator System

**Location**: `src/faststate/state.py`

The event system automatically creates HTTP endpoints for state methods.

### Event Decorator Implementation

```python
def event(path: str = None, method: str = "post", selector: str = "#updates", 
         merge_mode: str = "morph", **route_kwargs):
    """
    Decorator for creating reactive event handlers.
    
    Args:
        path: Custom URL path (default: /{ClassName}/{method_name})
        method: HTTP method (default: "post")
        selector: CSS selector for Datastar targeting (default: "#updates")
        merge_mode: Datastar merge mode (default: "morph")
        **route_kwargs: Additional FastHTML route arguments
    """
    def decorator(func):
        # Store event configuration on the function
        func._event_config = {
            'path': path,
            'method': method,
            'selector': selector,
            'merge_mode': merge_mode,
            'route_kwargs': route_kwargs
        }
        
        # Mark function as an event handler
        func._is_event = True
        
        # Create wrapper that handles state capture and SSE generation
        @wraps(func)
        def event_wrapper(self, *args, **kwargs):
            # Capture state before modification
            old_state = self.model_dump()
            
            # Execute original method
            result = func(self, *args, **kwargs)
            
            # If method returns custom response, use it
            if result is not None:
                return result
            
            # Otherwise, generate automatic SSE response
            new_state = self.model_dump()
            return self._diff_and_events(old_state, new_state)
        
        return event_wrapper
    
    return decorator
```

### Route Registration Process

When a `ReactiveState` class is defined, the metaclass automatically registers event routes:

```python
class ReactiveStateMeta(type):
    """Metaclass for ReactiveState that auto-registers event routes."""
    
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        
        # Find event methods
        for attr_name, attr_value in attrs.items():
            if hasattr(attr_value, '_is_event'):
                register_event_route(new_class, attr_name, attr_value)
        
        return new_class

def register_event_route(state_cls, method_name, method_func):
    """Register FastHTML route for event method."""
    config = method_func._event_config
    
    # Generate route path
    if config['path']:
        route_path = config['path']
    else:
        route_path = f"/{state_cls.__name__}/{method_name}"
    
    # Create route handler
    def route_handler(request: Request, session: dict):
        # Get state instance
        state = _get_state(state_cls, request, session)
        
        # Extract parameters from request
        params = extract_parameters(request, method_func)
        
        # Call event method
        return method_func(state, **params)
    
    # Register with FastHTML router
    rt.route(route_path, methods=[config['method'].upper()])(route_handler)
```

### Parameter Extraction

```python
def extract_parameters(request: Request, method_func) -> dict:
    """Extract and convert parameters for event method."""
    sig = inspect.signature(method_func)
    params = {}
    
    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue
            
        # Extract from query params or form data
        if request.method == "GET":
            value = request.query_params.get(param_name)
        else:
            # Handle both form data and JSON
            if request.headers.get('content-type') == 'application/json':
                json_data = request.json()
                value = json_data.get(param_name)
            else:
                form_data = request.form()
                value = form_data.get(param_name)
        
        # Type conversion
        if value is not None and param.annotation != inspect.Parameter.empty:
            value = convert_parameter(value, param.annotation)
        
        params[param_name] = value
    
    return params

def convert_parameter(value: str, target_type: type):
    """Convert string parameter to target type."""
    if target_type == str:
        return value
    elif target_type == int:
        return int(value)
    elif target_type == float:
        return float(value)
    elif target_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    else:
        # For complex types, attempt JSON parsing
        try:
            return json.loads(value)
        except:
            return value
```

---

## SSE Response Generation

### Diff Calculation

```python
def _diff_and_events(self, old_state: dict, new_state: dict) -> Any:
    """
    Generate SSE response with state changes.
    
    The diff calculation finds all changed properties between old and new state,
    then formats them as a Datastar-compatible SSE response.
    """
    changes = {}
    
    # Find changed properties
    for key, new_value in new_state.items():
        if key not in old_state or old_state[key] != new_value:
            changes[key] = new_value
    
    # Find removed properties
    for key in old_state:
        if key not in new_state:
            changes[key] = None  # Signal removal
    
    if changes:
        # Create SSE response with datastar-merge-signals event
        sse_data = f"event: datastar-merge-signals\ndata: {json.dumps(changes)}\n\n"
        return Response(content=sse_data, media_type="text/plain")
    
    # No changes, return empty response
    return Response(content="", media_type="text/plain")
```

### SSE Event Types

FastState supports different SSE event types for various use cases:

#### 1. datastar-merge-signals
Standard state updates that merge into client signals:

```python
event: datastar-merge-signals
data: {"count": 42, "message": "Updated"}
```

#### 2. datastar-merge-fragments  
HTML fragment updates for dynamic UI changes:

```python
@event(selector="#status-panel", merge_mode="inner")
def update_status(self, status: str):
    self.status = status
    # Return HTML fragment
    return Div(f"Status: {status}", cls="status-panel")
```

#### 3. Custom Events
Application-specific events for complex interactions:

```python
@event
def complex_operation(self, data: dict):
    result = self.process_data(data)
    
    # Return custom SSE event
    return f"event: custom-notification\ndata: {json.dumps(result)}\n\n"
```

### Client-Side Integration

The SSE responses automatically integrate with Datastar on the client:

```html
<!-- Datastar automatically handles these attributes -->
<div data-signals='{"count": 0, "message": "Hello"}' id="updates">
    <span data-text="$count"></span>
    <span data-text="$message"></span>
    
    <!-- Events automatically trigger SSE endpoints -->
    <button data-on-click="increment({amount: 1})">Increment</button>
</div>
```

### Performance Optimizations

#### 1. Minimal Diffs
Only changed properties are sent to reduce bandwidth:

```python
# Instead of sending entire state:
{"id": "123", "count": 42, "message": "Hello", "created_at": "2024-01-01"}

# Only send changes:
{"count": 42}  # Only count changed
```

#### 2. Efficient Serialization
Uses `model_dump()` for fast JSON serialization with Pydantic optimizations.

#### 3. Connection Reuse
Single SSE connection per client handles all state updates, reducing overhead.

#### 4. Automatic Cleanup
Stale state instances are cleaned up based on TTL and session expiration.

This completes the detailed documentation of all core FastState components. Each component is designed to work together seamlessly while maintaining clear separation of concerns and high performance.