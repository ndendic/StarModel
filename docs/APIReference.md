# FastState API Reference

This document provides a complete API reference for all FastState classes, functions, and decorators.

## Table of Contents

1. [Core Classes](#core-classes)
2. [Decorators](#decorators)
3. [Configuration](#configuration)
4. [Registry System](#registry-system)
5. [Integration Functions](#integration-functions)
6. [Utility Functions](#utility-functions)

---

## Core Classes

### ReactiveState

**Module**: `faststate.state`

Base class for all reactive state management. Inherits from SQLModel for data validation and persistence.

```python
class ReactiveState(SQLModel):
    """Base class for reactive state management with automatic SSE generation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique identifier for the state instance (auto-generated UUID4) |

#### Methods

##### `model_dump() -> dict`
Returns the state as a dictionary for JSON serialization.

**Returns**: `dict` - State data as key-value pairs

**Example**:
```python
state = MyState(count=42, message="Hello")
data = state.model_dump()  # {"id": "...", "count": 42, "message": "Hello"}
```

##### `_diff_and_events(old_state: dict, new_state: dict) -> Response`
Generate SSE response with state changes.

**Parameters**:
- `old_state` (`dict`): Previous state data
- `new_state` (`dict`): Current state data

**Returns**: `Response` - FastHTML Response object with SSE data

**Example**:
```python
old = {"count": 0}
new = {"count": 1}
response = state._diff_and_events(old, new)
# Generates: event: datastar-merge-signals\ndata: {"count": 1}\n\n
```

##### `__ft__() -> FT`
Render state as FastHTML component for direct template use.

**Returns**: `FT` - FastHTML component tree

**Example**:
```python
class MyState(ReactiveState):
    count: int = 0
    
    def __ft__(self):
        return Div(
            H3("Counter"),
            P(f"Count: {self.count}"),
            Button("Increment", onclick="increment()")
        )

# Usage in template
@rt('/')
def home(state: MyState):
    return Titled("Home", state)  # Calls __ft__ automatically
```

---

## Decorators

### @event

**Module**: `faststate.state`

Decorator for creating reactive event handlers that automatically generate HTTP endpoints and SSE responses.

```python
def event(
    path: str = None,
    method: str = "post", 
    selector: str = "#updates",
    merge_mode: str = "morph",
    **route_kwargs
) -> Callable
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str` | `None` | Custom URL path (default: `/{ClassName}/{method_name}`) |
| `method` | `str` | `"post"` | HTTP method for the endpoint |
| `selector` | `str` | `"#updates"` | CSS selector for Datastar targeting |
| `merge_mode` | `str` | `"morph"` | Datastar merge mode (`morph`, `inner`, `outer`, `append`, `prepend`, `delete`) |
| `**route_kwargs` | | | Additional FastHTML route parameters |

#### Examples

##### Basic Event
```python
class CounterState(ReactiveState):
    count: int = 0
    
    @event
    def increment(self, amount: int = 1):
        """Creates POST endpoint at /CounterState/increment"""
        self.count += amount
```

##### Custom Path and Method
```python
@event("/api/custom-increment", method="put")
def custom_increment(self, value: int):
    """Creates PUT endpoint at /api/custom-increment"""
    self.count = value
```

##### Custom Selector and Merge Mode
```python
@event(selector="#notification-area", merge_mode="append")
def add_notification(self, message: str):
    """Appends new content to #notification-area"""
    self.notifications.append(message)
    return Div(message, cls="notification")  # HTML to append
```

##### Return Custom Response
```python
@event
def validate_input(self, data: str):
    """Return custom HTML response"""
    if not data:
        return Div("Input required", cls="error")
    
    self.validated_data = data
    return Div("Valid input", cls="success")
```

#### Generated Endpoints

When you define an event method, FastState automatically creates:

1. **HTTP Endpoint**: `/{ClassName}/{method_name}` (or custom path)
2. **Parameter Extraction**: From query params, form data, or JSON body
3. **Type Conversion**: Based on method parameter annotations
4. **SSE Response**: Automatic state diff generation
5. **Error Handling**: Graceful error responses for invalid inputs

---

## Configuration

### StateScope

**Module**: `faststate.registry`

Enumeration defining different state isolation scopes.

```python
class StateScope(Enum):
    GLOBAL = "global"        # Shared across all users
    SESSION = "session"      # Per user session (default)
    USER = "user"           # Per authenticated user across sessions
    COMPONENT = "component"  # Per component instance
    RECORD = "record"       # Tied to specific database record
```

#### Scope Behaviors

| Scope | Key Pattern | Lifecycle | Use Cases |
|-------|-------------|-----------|-----------|
| `GLOBAL` | `global:{ClassName}` | Application lifetime | System settings, counters, feature flags |
| `SESSION` | `session:{ClassName}:{session_id}` | User session | Shopping cart, form data, UI state |
| `USER` | `user:{ClassName}:{user_id}` | User account | Profile, preferences, saved data |
| `COMPONENT` | `component:{ClassName}:{component_id}` | Component lifetime | Widget state, modal state |
| `RECORD` | `record:{ClassName}:{record_id}` | Database record | Document editing, entity state |

### StateConfig

**Module**: `faststate.registry`

Configuration dataclass for state registration.

```python
@dataclass
class StateConfig:
    scope: StateScope = StateScope.SESSION
    ttl: Optional[int] = None
    auto_persist: bool = False
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `scope` | `StateScope` | `SESSION` | State isolation scope |
| `ttl` | `Optional[int]` | `None` | Time to live in seconds (None = no expiration) |
| `auto_persist` | `bool` | `False` | Automatically save state changes to database |

#### Examples

```python
# Session-scoped with 1 hour TTL
StateConfig(
    scope=StateScope.SESSION,
    ttl=3600
)

# User-scoped with auto-persistence
StateConfig(
    scope=StateScope.USER,
    auto_persist=True
)

# Global scope (no TTL, shared across all users)
StateConfig(scope=StateScope.GLOBAL)

# Record-scoped with auto-persistence and 30 minute TTL
StateConfig(
    scope=StateScope.RECORD,
    auto_persist=True,
    ttl=1800
)
```

---

## Registry System

### FastStateRegistry

**Module**: `faststate.registry`

Central registry managing state types, configurations, and instance caching.

```python
class FastStateRegistry:
    def __init__(self):
        self._state_configs: Dict[Type, StateConfig] = {}
        self._state_instances: Dict[str, 'ReactiveState'] = {}
```

#### Methods

##### `register(state_cls: Type[ReactiveState], config: StateConfig) -> None`
Register a state class for automatic dependency injection.

**Parameters**:
- `state_cls` (`Type[ReactiveState]`): State class to register
- `config` (`StateConfig`): Configuration for the state class

**Example**:
```python
state_registry.register(
    MyState,
    StateConfig(scope=StateScope.SESSION)
)
```

##### `is_state_type(annotation: Any) -> bool`
Check if a type annotation represents a registered state type.

**Parameters**:
- `annotation` (`Any`): Type annotation to check

**Returns**: `bool` - True if annotation is a registered state type

**Example**:
```python
assert state_registry.is_state_type(MyState) == True
assert state_registry.is_state_type(str) == False
assert state_registry.is_state_type(Optional[MyState]) == True  # Handles generics
```

##### `resolve_state(state_cls: Type, req: Request, sess: dict, auth: Optional[str] = None) -> ReactiveState`
Resolve state instance based on registered configuration.

**Parameters**:
- `state_cls` (`Type`): State class to resolve
- `req` (`Request`): FastHTML request object
- `sess` (`dict`): Session dictionary
- `auth` (`Optional[str]`): Authentication string

**Returns**: `ReactiveState` - State instance for the given scope and context

**Raises**:
- `ValueError`: If required parameters are missing (e.g., record_id for RECORD scope)

**Example**:
```python
# Manual state resolution (usually handled automatically)
state = state_registry.resolve_state(MyState, req, sess, auth)
```

##### `get_config(state_cls: Type) -> Optional[StateConfig]`
Get configuration for a registered state class.

**Parameters**:
- `state_cls` (`Type`): State class to get config for

**Returns**: `Optional[StateConfig]` - Configuration if registered, None otherwise

##### `clear_instance_cache() -> None`
Clear all cached state instances. Useful for testing.

##### `get_cached_instances() -> Dict[str, ReactiveState]`
Get all cached state instances. Useful for debugging.

**Returns**: `dict` - Copy of cached instances by state key

#### Global Registry Instance

```python
# Global registry instance - use this in your application
from faststate import state_registry

state_registry.register(MyState, StateConfig())
```

---

## Integration Functions

### initialize_faststate

**Module**: `faststate.fasthtml_integration`

Initialize FastState integration with FastHTML by monkey patching the dependency injection system.

```python
def initialize_faststate() -> bool
```

**Returns**: `bool` - True if initialization successful, False if FastHTML not available

**Example**:
```python
from faststate import initialize_faststate

# Call once during application startup
success = initialize_faststate()
if success:
    print("FastState integration active")
else:
    print("FastHTML not available - manual state management required")
```

**What it does**:
1. Monkey patches `FastHTML.add_route` method
2. Adds automatic state type detection
3. Creates injection wrappers for routes with state parameters
4. Preserves existing FastHTML DI for `req`, `sess`, `auth` parameters

### create_state_middleware

**Module**: `faststate.fasthtml_integration`

Create middleware for setting up state context (alternative to monkey patching).

```python
def create_state_middleware() -> Callable
```

**Returns**: `Callable` - Middleware function for FastHTML/Starlette

**Example**:
```python
from faststate import create_state_middleware

# Alternative to monkey patching
middleware = create_state_middleware()
app.add_middleware(middleware)
```

### get_state_info

**Module**: `faststate.fasthtml_integration`

Get information about registered states and current status for debugging.

```python
def get_state_info() -> dict
```

**Returns**: `dict` - Registry information

**Response Structure**:
```python
{
    "registered_states": [
        {
            "class_name": "MyState",
            "scope": "session",
            "auto_persist": False,
            "ttl": None
        }
    ],
    "cached_instances": 5,  # Number of cached instances
    "integration_active": True
}
```

**Example**:
```python
info = get_state_info()
print(f"Registered: {len(info['registered_states'])}")
print(f"Cached: {info['cached_instances']}")
```

---

## Utility Functions

### _get_state

**Module**: `faststate.state`

Legacy function for manual state retrieval (use automatic injection instead).

```python
def _get_state(state_cls: Type[ReactiveState], request: Request, session: dict) -> ReactiveState
```

**Parameters**:
- `state_cls` (`Type[ReactiveState]`): State class to retrieve
- `request` (`Request`): FastHTML request object
- `session` (`dict`): Session dictionary

**Returns**: `ReactiveState` - State instance

**Example**:
```python
# Legacy approach (avoid in new code)
@rt('/')
def home(req: Request, sess: dict):
    state = _get_state(MyState, req, sess)
    return render_template(state)

# Preferred approach (automatic injection)
@rt('/')
def home(state: MyState):
    return render_template(state)
```

---

## Type Annotations

### Common Type Patterns

#### Optional State Parameters
```python
@rt('/optional')
def optional_route(state: Optional[MyState] = None):
    """State parameter is optional"""
    if state is None:
        return Div("No state available")
    return state.__ft__()
```

#### Multiple State Injection
```python
@rt('/multi')
def multi_state_route(
    counter: CounterState,
    user: UserProfile,
    settings: AppSettings
):
    """Multiple states automatically injected"""
    return Div(counter, user, settings)
```

#### Mixed Parameters
```python
@rt('/mixed/{item_id}')
def mixed_route(
    req: Request,
    sess: dict,
    auth: str,
    item_id: int,
    state: ItemState
):
    """Mix of FastHTML DI and FastState injection"""
    # All parameters automatically injected
    pass
```

---

## Error Handling

### Common Exceptions

#### ValueError
Raised when required parameters are missing for state resolution.

```python
# Record scope requires record_id
@rt('/edit')  # Missing {record_id} in path
def edit(doc: DocumentState):  # Will raise ValueError
    pass

# Solution: Include required parameter
@rt('/edit/{record_id}')
def edit(record_id: int, doc: DocumentState):
    pass
```

#### ImportError
Raised when FastHTML is not available during initialization.

```python
try:
    success = initialize_faststate()
except ImportError:
    print("FastHTML not installed")
    success = False
```

### Error Response Patterns

#### Event Handler Errors
```python
@event
def risky_operation(self, data: str):
    try:
        result = process_data(data)
        self.result = result
    except ValidationError as e:
        # Return error fragment without updating state
        return Div(f"Error: {e}", cls="error")
    except Exception as e:
        logger.exception("Unexpected error")
        return Div("Operation failed", cls="error")
```

#### Route-Level Error Handling
```python
@rt('/protected')
def protected_route(state: UserState, auth: str = None):
    if not auth:
        return Div("Authentication required", cls="error")
    
    try:
        return state.__ft__()
    except Exception as e:
        logger.exception("Route error")
        return Div("Internal server error", cls="error")
```

---

## Best Practices

### 1. Type Annotations
Always use type annotations for state parameters:

```python
# Good
def route(state: MyState):
    pass

# Bad - won't work
def route(state):
    pass
```

### 2. State Registration
Register states early in application lifecycle:

```python
# Good - register during startup
initialize_faststate()
state_registry.register(MyState, StateConfig())

# Bad - registering in route handler
@rt('/')
def home():
    state_registry.register(MyState, StateConfig())  # Too late
```

### 3. Event Return Values
Return appropriate responses from event handlers:

```python
@event
def update_data(self, value: str):
    if not value:
        # Return error without updating state
        return Div("Value required", cls="error")
    
    self.data = value
    # Automatic SSE response generated for state changes
```

### 4. Scope Selection
Choose appropriate scope for your use case:

```python
# User preferences - USER scope
state_registry.register(UserPrefs, StateConfig(scope=StateScope.USER))

# Shopping cart - SESSION scope  
state_registry.register(Cart, StateConfig(scope=StateScope.SESSION))

# System settings - GLOBAL scope
state_registry.register(Settings, StateConfig(scope=StateScope.GLOBAL))

# Document editing - RECORD scope
state_registry.register(DocEditor, StateConfig(scope=StateScope.RECORD))
```

This completes the comprehensive API reference for FastState. All classes, functions, and patterns are documented with examples and best practices.