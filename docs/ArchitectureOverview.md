# FastState Architecture Overview

## Introduction

FastState is a reactive state management system that integrates with FastHTML to provide automatic dependency injection, real-time state synchronization, and clean separation of concerns. This document provides a comprehensive technical overview of how all components work together.

## Core Philosophy

FastState follows these key principles:

1. **Zero Configuration Dependency Injection**: State instances are automatically injected into route functions based on type annotations
2. **Reactive State Management**: Changes to state automatically trigger SSE updates to connected clients
3. **Scope-Based State Isolation**: Different state scopes (SESSION, USER, GLOBAL, RECORD) provide appropriate data isolation
4. **FastHTML Integration**: Seamless integration with FastHTML's existing DI system through monkey patching
5. **Separation of Concerns**: Authentication handled via FastHTML beforeware, state management focused purely on reactivity

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastHTML Application                    │
├─────────────────────────────────────────────────────────────────┤
│                    FastHTML Beforeware                         │
│                   (Authentication)                             │
├─────────────────────────────────────────────────────────────────┤
│                FastState Integration Layer                     │
│              (Monkey Patch + DI Extension)                     │
├─────────────────────────────────────────────────────────────────┤
│     Route Handler     │    State Registry    │   SSE Events    │
│   (Auto Injection)   │   (Scope Management) │ (Real-time UI)  │
├─────────────────────────────────────────────────────────────────┤
│                    State Classes                       │
│              (Business Logic + Event Handlers)                 │
├─────────────────────────────────────────────────────────────────┤
│                    SQLModel/Pydantic                          │
│                (Data Validation + Persistence)                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Interaction Flow

### 1. Application Startup

```python
# 1. Initialize FastState integration
initialize_faststate()  # Monkey patches FastHTML's add_route method

# 2. Register state types with configurations
state_registry.register(MyState, StateConfig(scope=StateScope.SESSION))

# 3. Create FastHTML app with beforeware
app, rt = fast_app(before=auth_beforeware)
```

### 2. Route Registration

When a route is registered, the monkey-patched `add_route` method:

1. **Inspects function signature** for state type annotations
2. **Creates wrapper function** that injects state instances
3. **Preserves original FastHTML DI** for `req`, `sess`, `auth` parameters
4. **Registers enhanced route** with FastHTML

```python
# Original route definition
@rt('/profile')
def profile(req: Request, sess: dict, profile: UserProfileState, auth: str = None):
    return Titled("Profile", profile.render())

# What happens internally:
# 1. FastState detects `UserProfileState` annotation
# 2. Creates wrapper that calls state_registry.resolve_state()
# 3. Injects resolved state instance into route function
# 4. Original function receives fully initialized state
```

### 3. State Resolution Process

When a route with state parameters is called:

```
Request → FastHTML Router → Enhanced Route Wrapper → State Registry
   ↓
State Registry:
1. Gets state configuration (scope, TTL, persistence)
2. Generates hierarchical state key based on scope
3. Checks instance cache for existing state
4. Creates new state instance if needed
5. Stores in cache with generated key
   ↓
Route Function ← Injected State Instance ← State Registry
```

### 4. Event Handling and SSE

```python
class MyState(State):
    count: int = 0
    
    @event  # Automatically creates /MyState/increment endpoint
    def increment(self, amount: int):
        old_state = self.model_dump()
        self.count += amount
        new_state = self.model_dump()
        
        # Automatic SSE response generation
        return self._diff_and_events(old_state, new_state)
```

Event flow:
1. **Client triggers event** via Datastar `data-on-*` attributes
2. **HTTP request** sent to auto-generated endpoint
3. **State updated** in event handler method
4. **SSE response generated** with state diffs
5. **Client receives updates** and updates UI reactively

## State Scopes Deep Dive

### SESSION Scope
- **Key Pattern**: `session:{ClassName}:{session_id}`
- **Lifecycle**: Tied to user session
- **Use Cases**: User preferences, shopping cart, form data
- **Isolation**: Each session gets independent state

### USER Scope  
- **Key Pattern**: `user:{ClassName}:{user_id}`
- **Lifecycle**: Persists across sessions for authenticated users
- **Use Cases**: User profile, settings, persistent data
- **Isolation**: States shared across user's sessions

### GLOBAL Scope
- **Key Pattern**: `global:{ClassName}`
- **Lifecycle**: Shared across all users
- **Use Cases**: System configuration, announcements, global counters
- **Isolation**: Single instance for entire application

### RECORD Scope
- **Key Pattern**: `record:{ClassName}:{record_id}`
- **Lifecycle**: Tied to specific database records
- **Use Cases**: Document editing, product management, entity-specific state
- **Isolation**: Separate state per record ID

## FastHTML Integration Details

### Monkey Patch Implementation

FastState extends FastHTML's dependency injection by monkey patching the `FastHTML.add_route` method:

```python
def enhanced_add_route(self, *args, **kwargs):
    # Handle different FastHTML call patterns
    if len(args) >= 2:
        path, endpoint = args[0], args[1]
        
        # Inspect function signature for state types
        sig = inspect.signature(endpoint)
        state_params = []
        for param_name, param in sig.parameters.items():
            if state_registry.is_state_type(param.annotation):
                state_params.append((param_name, param.annotation))
        
        if state_params:
            # Create injection wrapper
            @wraps(endpoint)
            def state_injecting_wrapper(*args, **kwargs):
                # Extract FastHTML parameters
                req = kwargs.get('req')
                sess = kwargs.get('sess') 
                auth = kwargs.get('auth')
                
                # Inject state instances
                for param_name, state_type in state_params:
                    if param_name not in kwargs:
                        state_instance = state_registry.resolve_state(
                            state_type, req, sess, auth
                        )
                        kwargs[param_name] = state_instance
                
                # Call original function with injected states
                return endpoint(*args, **kwargs)
            
            endpoint = state_injecting_wrapper
    
    # Call original add_route with enhanced endpoint
    return original_add_route(self, path, endpoint, *remaining_args, **kwargs)
```

### Why Monkey Patching?

1. **Seamless Integration**: Works with existing FastHTML patterns
2. **Zero Configuration**: No middleware setup required
3. **Backward Compatibility**: Existing routes continue to work
4. **Type Safety**: Leverages Python type annotations
5. **Performance**: Injection happens only for routes with state parameters

## Data Flow Architecture

### State Creation and Caching

```
Route Call → State Resolution → Cache Check → Instance Creation
     ↓              ↓               ↓             ↓
FastHTML DI → Registry Lookup → Hit: Return → New Instance
     ↓              ↓               ↓             ↓
Enhanced    → Config Retrieval → Miss: Create → Cache Store
Route       → Key Generation                   → Return Instance
```

### SSE Response Generation

```
Event Handler → State Mutation → Diff Calculation → SSE Response
      ↓              ↓               ↓                ↓
@event Method → Model Changes → Old vs New → datastar-merge-signals
      ↓              ↓               ↓                ↓
HTTP Endpoint → Property Updates → JSON Diff → Client Update
```

### Client-Server Synchronization

```
Client State ←→ Datastar Signals ←→ SSE Events ←→ Server State
     ↓                ↓                ↓              ↓
DOM Updates ← Signal Updates ← datastar-merge ← Event Response
     ↓                ↓                ↓              ↓
User Interaction → Event Triggers → HTTP Request → State Mutation
```

## Performance Considerations

### State Instance Caching

- **Memory Efficient**: States cached by hierarchical keys
- **TTL Support**: Automatic cleanup of expired states
- **Scope Isolation**: Different scopes don't interfere
- **Session Cleanup**: States removed when sessions expire

### SSE Optimization

- **Diff-Based Updates**: Only changed properties sent to client
- **Efficient Serialization**: JSON-based state transmission  
- **Connection Reuse**: Single SSE connection per client
- **Automatic Reconnection**: Client handles connection drops

### Database Integration

- **Lazy Loading**: States created only when accessed
- **Auto Persistence**: Optional automatic database saves
- **Connection Pooling**: Efficient database usage
- **Transaction Support**: Atomic state updates

## Security Model

### Authentication Integration

FastState delegates authentication to FastHTML's standard beforeware pattern:

```python
def auth_beforeware(req, sess):
    """Handle authentication outside of state system"""
    return sess.get('auth')  # Returns auth user or None

app, rt = fast_app(before=auth_beforeware)
```

### Authorization Patterns

Authorization is handled at the route level, not in the state system:

```python
@rt('/admin')
def admin_panel(req, sess, auth, settings: GlobalSettingsState):
    # Route-level authorization check
    if not auth or not has_admin_permission(auth):
        return Redirect('/login')
    
    # Proceed with authorized access to state
    return settings.render_admin_panel()
```

### State Isolation

- **Scope-Based Security**: Different scopes provide natural isolation
- **Session Security**: FastHTML's cryptographic session signing
- **No State Leakage**: Proper key generation prevents cross-user access
- **Request Context**: Auth information available for route-level checks

## Error Handling

### State Resolution Errors

```python
try:
    state = state_registry.resolve_state(StateType, req, sess, auth)
except ValueError as e:
    # Missing required parameters (e.g., record_id for RECORD scope)
    return error_response(f"Invalid request: {e}")
except Exception as e:
    # Other state resolution issues
    logger.error(f"State resolution failed: {e}")
    return error_response("Internal server error")
```

### Event Handler Errors

```python
@event
def risky_operation(self, data: str):
    try:
        # Potentially failing operation
        result = process_data(data)
        self.result = result
    except ValidationError as e:
        # Return error fragment instead of updating state
        return Div(f"Validation error: {e}", cls="error")
    except Exception as e:
        logger.error(f"Event handler failed: {e}")
        return Div("Operation failed", cls="error")
```

## Extension Points

### Custom State Scopes

Extend the `StateScope` enum and update the key generation logic:

```python
class StateScope(Enum):
    # ... existing scopes
    TENANT = "tenant"  # Multi-tenant applications
    
def _generate_state_key(self, state_cls, config, req, sess, auth):
    # ... existing scope handling
    case StateScope.TENANT:
        tenant_id = get_tenant_from_request(req)
        return f"tenant:{class_name}:{tenant_id}"
```

### Custom Persistence

Implement custom persistence by extending the registry:

```python
def _load_from_persistence(self, state_cls, record_id):
    """Custom persistence implementation"""
    if hasattr(state_cls, 'load_from_db'):
        return state_cls.load_from_db(record_id)
    return None
```

### Middleware Integration

Add custom middleware for state preprocessing:

```python
def state_middleware():
    def middleware(request, call_next):
        # Pre-process state context
        setup_state_context(request)
        response = call_next(request)
        # Post-process state updates
        cleanup_state_context(request)
        return response
    return middleware
```

This architecture provides a solid foundation for building reactive web applications with automatic state management, real-time updates, and clean separation of concerns.