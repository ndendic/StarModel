# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run the application**: `python app/main.py` or `python -m app.main`
- **Install dependencies**: `uv sync` (uses uv for dependency management)
- **Add dependencies**: `uv add <package-name>`
- **Install dev dependencies**: `uv sync --group dev`
- **Run tests**: `python test_<test_name>.py` (tests are standalone scripts)
- **Run all tests**: Execute individual test files directly (no unified test runner configured)
- **Run specific tests**:
  - SSE tests: `python test_sse_manager.py`
  - Persistence tests: `python test_persistence.py`
  - Integration tests: `python test_integration.py`
  - Registry tests: `python test_registry.py`
  - FastHTML integration tests: `python test_fasthtml_integration.py`
  - Auth tests: `python test_auth.py`
  - App integration tests: `python test_app_integration.py`

## Project Architecture

StarModel is a reactive state management system that integrates FastHTML with Datastar for building interactive web applications entirely in Python. The architecture follows these key patterns:

### Core Components

1. **State Base Class** (`src/starmodel/state.py`): 
   - Inherits from Pydantic BaseModel for data validation and serialization
   - Provides simple `.get(req)` class method for explicit state resolution
   - **Signal-based Architecture**: Uses `SignalModelMeta` metaclass to create signal descriptors for Datastar integration
   - **StateStore Enumeration**: Direct configuration using `StateStore` enum (CLIENT_SESSION, CLIENT_LOCAL, SERVER_MEMORY, CUSTOM)
   - **model_config**: Uses Pydantic's model_config dictionary for all state configuration options
   - Automatically generates SSE endpoints for `@event` decorated methods
   - Handles state synchronization between server and client via Datastar signals
   - Built-in methods for live streaming (`live`), polling (`poll`), and syncing (`sync`)

2. **Event Decorator System**:
   - `@event` decorator automatically registers methods as HTTP endpoints
   - **URL Generator Methods**: Automatically creates static methods for Datastar attributes (e.g., `MyState.increment(1)` → `@get('/MyState/increment?amount=1')`)
   - Supports custom routing paths, HTTP methods, and Datastar selectors with `merge_mode` parameter
   - Uses FastHTML's APIRouter for route registration
   - Generates SSE responses for real-time state updates
   - Handles parameter conversion from query strings, JSON payloads, and Datastar payload
   - Always sends `merge_signals` for state sync, conditionally sends `merge_fragments` for FT components

3. **Signal System**:
   - **SignalDescriptor**: Creates reactive bindings for Pydantic model fields
   - **SignalModelMeta**: Metaclass that automatically adds signal descriptors for each field
   - Returns `$FieldName` for class access and actual values for instance access
   - Supports namespaced signals (e.g., `$ClassName.fieldname`)
   - Field signal methods (e.g., `myfield_signal`) for programmatic access

4. **Persistence Layer** (`src/starmodel/persistence.py`):
   - **StatePersistenceBackend**: Abstract base class for persistence implementations
   - **MemoryStatePersistence**: In-memory implementation with TTL support
   - Supports both async and sync operations for flexibility
   - Built-in memory_persistence instance for immediate use
   - Future-ready for Redis and Database backends (currently commented out)

### Key Patterns

- **State classes** inherit from `State` and define reactive properties with automatic signal generation
- **Simple state access** via `MyState.get(req)` method for explicit resolution with session-based caching
- **Event methods** use `@event` decorator for automatic route registration with URL generators
- **UI binding** uses Datastar `data-*` attributes with automatic signal names (`$fieldname` or `$ClassName.fieldname`)
- **State updates** automatically trigger SSE events to update client signals via `merge_signals`
- **Session management** ties state instances to sessions via automatic ID generation and memory persistence
- **Real-time streaming** via `live()`, `poll()`, and `sync()` built-in methods
- **Automatic persistence** with configurable StateStore backends and TTL support
- **Client-side persistence** support for sessionStorage and localStorage via Datastar

### Technology Stack

- **FastHTML**: Server-side HTML generation and routing
- **Datastar**: Client-side reactivity and SSE handling (~15KB, uses SSE transport)
- **Pydantic**: Data validation and serialization (BaseModel)
- **MonsterUI**: UI component library for styling

### State Management Flow

1. State class defines reactive properties and event handlers with optional configuration
2. Route handlers use `MyState.get(req)` to access state instances (auto-registers on first access)
3. UI renders with `data-signals` containing initial state
4. User interactions trigger events via Datastar `data-on-*` attributes using generated URL methods
5. Event handlers update state and return SSE responses with `merge_signals` and optional `merge_fragments`
6. Client receives SSE updates and automatically updates bound UI elements

### State Configuration Examples

```python
# Simple state with default configuration (SERVER_MEMORY store, auto_persist enabled)
class MyState(State):
    myInt: int = 0
    myStr: str = "Hello"
    
    @event
    def increment(self, amount: int):
        self.myInt += amount

# State with custom configuration using model_config
class CounterState(State):
    count: int = 0
    last_updated_by: str = ""
    
    model_config = {
        "store": StateStore.CLIENT_SESSION,  # Use sessionStorage
        "use_namespace": True,               # Enable namespaced signals
        "auto_persist": False                # Disable auto-persist for client storage
    }
    
    @event(method="post")
    def increment(self, amount: int = 1, user: str = "Anonymous"):
        self.count += amount
        self.last_updated_by = user

# Simple route usage with .get() method
@rt('/')
def index(req: Request):
    my_state = MyState.get(req)  # Auto-caches with memory persistence
    return Main(
        my_state,  # Uses __ft__ method for rendering with data-signals
        Button("+1", data_on_click=MyState.increment(1)),  # Generated URL method
        P(f"Count: {my_state.myInt}")  # Direct access to values
    )
```

### Configuration Options

**StateStore enum values:**
- `StateStore.CLIENT_SESSION` - Browser sessionStorage (Datastar managed)
- `StateStore.CLIENT_LOCAL` - Browser localStorage (Datastar managed)
- `StateStore.SERVER_MEMORY` - Server-side memory persistence (default)
- `StateStore.CUSTOM` - Custom persistence backend

**model_config parameters:**
- `store: StateStore` - Storage mechanism (default: SERVER_MEMORY)
- `auto_persist: bool` - Enable automatic persistence (default: True)
- `persistence_backend: StatePersistenceBackend` - Backend instance (default: memory_persistence)
- `use_namespace: bool` - Use namespaced signals (default: True)
- `namespace: str` - Custom namespace (default: class name)
- `sync_with_client: bool` - Sync with client changes (default: True)

### SSE and Streaming Patterns

- All event responses are SSE streams with proper headers
- **Automatic State Sync**: Always sends `merge_signals` with current state
- **Fragment Updates**: Conditionally sends `merge_fragments` for FastHTML components
- **Streaming Support**: Async generators for real-time streaming responses
- **Merge Modes**: Support for "morph", "inner", "outer", "append", "prepend" via `merge_mode` parameter

### Development Notes

- **Simple Configuration**: Use Pydantic's `model_config` dictionary for all state settings
- **State Access**: Use `MyState.get(req)` for simple, explicit state resolution with automatic caching
- **Smart Defaults**: Classes without custom `model_config` get SERVER_MEMORY store with auto_persist enabled
- **Session Management**: State instances automatically tied to sessions via `get_session_id()` method
- **Parameter Conversion**: Event handlers handle string-to-type conversion from query params and Datastar payload
- **Signal Access**: Use `my_state.signal('fieldname')` or `FieldName_signal` descriptor for reactive bindings
- **Custom Routing**: Custom routing paths can override default `ClassName/method_name` pattern
- **Clean Architecture**: No complex setup - just inherit from State and use `@event` decorator
- **URL Generators**: Automatic static methods for Datastar attributes via `__init_subclass__`

### Integration with FastHTML

- **Simple API**: Use `MyState.get(req)` in any FastHTML route handler
- **Route Registration**: `@event` decorated methods are auto-registered with FastHTML's APIRouter
- **Parameter Injection**: Compatible with FastHTML's dependency injection system
- **Backward Compatibility**: Works alongside existing FastHTML patterns
- **Module Structure**: Organized in `app/pages/` directory with automatic route collection
- **Clean Setup**: Just import and use - no complex configuration needed

### Real-time Features

- **Built-in Streaming**: `live()`, `poll()`, and `sync()` methods for real-time updates
- **SSE Responses**: All event methods return SSE streams with automatic signal updates
- **Heartbeat Support**: `live(heartbeat=1.0)` for periodic state updates
- **Async Generators**: Support for streaming responses with automatic state persistence

### Persistence Configuration

- **Memory Backend**: Built-in `MemoryStatePersistence` with TTL support for development
- **Client-side Storage**: sessionStorage and localStorage via Datastar integration
- **Custom Backends**: Extensible `StatePersistenceBackend` interface
- **Auto-persist**: Automatically save/load state changes with configurable persistence
- **Future Backends**: Redis and Database backends available in commented code

### Signal System Features

- **Automatic Signals**: Every field gets a corresponding signal descriptor
- **Namespaced Signals**: Optional class-based namespacing (e.g., `$ClassName.field`)
- **Signal Methods**: Built-in `signal()` method and `field_signal` descriptors
- **Datastar Integration**: Seamless integration with Datastar's reactive system
- **Client Persistence**: Automatic `data-persist` attributes for client storage

### Testing Structure

- Tests are standalone Python scripts (no pytest/unittest framework)
- Each test file can be run independently: `python test_<name>.py`
- Manual verification required as tests don't use assertion frameworks

### Demo Application Features

The demo app showcases all StarModel capabilities with modular page structure:

- **Home (`/`)**: MyState with default SESSION scope configuration
- **Counter (`/counter`)**: CounterState with GLOBAL scope and memory persistence 
- **Admin (`/admin`)**: GlobalSettingsState with GLOBAL scope and database persistence
- **Profile (`/profile`)**: UserProfileState with USER scope and database persistence
- **Product (`/product/{id}`)**: ProductState with RECORD scope tied to specific IDs
- **Chat (`/chat`)**: ChatState with GLOBAL scope for real-time collaboration
- **Auth (`/login`, `/auth-demo`)**: Authentication handling and session management
- **Status (`/status`)**: System monitoring dashboard with live statistics

### Page Module Structure

```
app/pages/
├── __init__.py
├── index.py          # MyState (default config)
├── counter.py         # CounterState (global, memory)
├── admin.py           # GlobalSettingsState (global, database) 
├── auth.py            # UserProfileState (user, database)
├── product.py         # ProductState (record, database)
└── chat.py            # ChatState (global, memory)
```

## Important Development Notes

- **Simple Setup**: States work out-of-the-box with minimal configuration
- **State Configuration**: Use Pydantic's `model_config` dictionary for custom settings
- **State Access Pattern**: Use `MyState.get(req)` in route handlers for explicit state resolution
- **State Lifecycle**: States are automatically cached in memory with session-based IDs
- **Database File**: Demo app uses SQLite database (`app/starmodel_demo.db`) for demo purposes
- **Authentication**: Compatible with FastHTML beforeware middleware system
- **Route Collection**: Automatic route discovery from `app/pages/` modules via FastHTML patterns
- **No Complex Setup**: Just inherit from State and use `@event` decorator
- **Backward Compatibility**: Existing FastHTML patterns work alongside StarModel enhancements

## Simple State Access API

```python
# Basic usage in any route (auto-caches with memory persistence)
my_state = MyState.get(req)

# Multiple states in one route
counter = CounterState.get(req)    # SERVER_MEMORY store
profile = ProfileState.get(req)    # CLIENT_SESSION store

# Generated URL methods for Datastar
Button("+1", data_on_click=MyState.increment(1))       # → @get('/MyState/increment?amount=1')
Button("Save", data_on_click=ProductState.save())      # → @get('/ProductState/save')
Button("Delete", data_on_click=ProductState.delete(confirm=True))  # → @get('/ProductState/delete?confirm=true')

# Signal access for reactive binding
Div(f"Count: {counter.count}", data_text=counter.count_signal)  # → data-text="$CounterState.count"
```

## Configuration Examples

```python
# Default configuration (SERVER_MEMORY store, auto_persist enabled)
class SimpleState(State):
    value: int = 0
    # No model_config needed - gets defaults automatically

# Custom client-side persistence
class SessionState(State):
    data: dict = {}
    
    model_config = {
        "store": StateStore.CLIENT_SESSION,  # Use sessionStorage
        "use_namespace": True,               # Enable namespacing
        "auto_persist": False                # Disable server auto-persist
    }

# Server-side with custom backend
class PersistentState(State):
    important_data: str = ""
    
    model_config = {
        "store": StateStore.SERVER_MEMORY,
        "auto_persist": True,
        "persistence_backend": memory_persistence  # Custom backend instance
    }
```