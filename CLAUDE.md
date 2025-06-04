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

FastState is a reactive state management system that integrates FastHTML with Datastar for building interactive web applications entirely in Python. The architecture follows these key patterns:

### Core Components

1. **State Base Class** (`src/faststate/state.py`): 
   - Inherits from Pydantic BaseModel for data validation and serialization
   - Provides simple `.get(req)` class method for explicit state resolution
   - **Auto-registration**: States automatically register themselves on first access using class-level configuration
   - **Simplified Configuration**: Uses single `_config: StateConfig` field for all state configuration
   - **Smart Defaults**: States without explicit config get sensible defaults (SESSION scope, no persistence)
   - Automatically generates SSE endpoints for `@event` decorated methods
   - Handles state synchronization between server and client via Datastar signals
   - Integrated with SSE broadcasting for real-time multi-user updates

2. **Event Decorator System**:
   - `@event` decorator automatically registers methods as HTTP endpoints
   - **URL Generator Methods**: Automatically creates static methods for Datastar attributes (e.g., `MyState.increment(1)` → `@get('/MyState/increment?amount=1')`)
   - Supports custom routing paths, HTTP methods, and Datastar selectors with `merge_mode` parameter
   - **Simplified Implementation**: Clean, streamlined architecture (~200 lines vs previous ~400 lines)
   - Generates SSE responses for real-time state updates
   - Handles parameter conversion from query strings and JSON payloads
   - Always sends `merge_signals` for state sync, conditionally sends `merge_fragments` for FT components

3. **State Registry** (`src/faststate/registry.py`):\
   - **Auto-registration**: No manual `state_registry.register()` calls needed
   - **StateScope Enum**: Direct enum usage (e.g., `StateScope.GLOBAL`) without string mappings
   - **StateConfig Dataclass**: Centralized configuration with Pydantic validation
   - Supports SESSION, GLOBAL, USER, RECORD, and COMPONENT scopes
   - Session-based state retrieval and management via `state_registry.resolve_state_sync()`
   - Automatic state lifecycle management and caching
   - Integrated with persistence layer for automatic state loading/saving
   - Powers the simple `.get()` method for explicit state resolution

4. **SSE Connection Manager** (`src/faststate/sse_manager.py`):\
   - Advanced SSE connection management with scope-aware broadcasting
   - Connection pooling and automatic cleanup for production reliability
   - Scope-specific broadcasting (global, session, user, record-based)
   - Health monitoring and connection statistics
   - Heartbeat mechanism and connection expiry handling

5. **Persistence Layer** (`src/faststate/persistence.py`):\
   - Multi-backend persistence system (Memory, Redis, Database)
   - Automatic state loading and saving with configurable TTL
   - Pluggable backend architecture for different storage needs
   - Production-ready with SQLAlchemy and Redis support
   - Supports both async and sync operations for flexibility

### Key Patterns

- **State classes** inherit from `State` and define reactive properties
- **Auto-registration**: States automatically register on first `.get()` call using class-level configuration
- **Simple state access** via `MyState.get(req)` method for explicit resolution
- **Event methods** use `@event` decorator for automatic route registration with URL generators
- **UI binding** uses Datastar `data-*` attributes for two-way binding
- **State updates** automatically trigger SSE events to update client signals
- **Session management** ties state instances to user sessions via registry
- **Real-time collaboration** via scope-aware SSE broadcasting
- **Automatic persistence** with configurable backends and TTL
- **Production monitoring** with connection stats and health checks

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
# Simple state with default configuration (SESSION scope, no persistence)
class MyState(State):
    myInt: int = 0
    myStr: str = "Hello"
    
    @event
    def increment(self, amount: int):
        self.myInt += amount

# Advanced state with explicit configuration
class CounterState(State):
    count: int = 0
    last_updated_by: str = ""
    
    # Auto-registration configuration
    _config = StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="database",
        ttl=3600
    )
    
    @event(method="post")
    def increment(self, amount: int = 1, user: str = "Anonymous"):
        self.count += amount
        self.last_updated_by = user

# Simple route usage with .get() method
@rt('/')
def index(req: Request, sess: dict, auth: str = None):
    my_state = MyState.get(req, sess, auth)  # Auto-registers with defaults
    return Main(
        my_state,  # Uses __ft__ method for rendering with data-signals
        Button("+1", data_on_click=MyState.increment(1)),  # Generated URL method
        Button("Reset", data_on_click=MyState.reset())
    )
```

### Configuration Options

**StateScope enum values:**
- `StateScope.SESSION` - Per user session (default)
- `StateScope.GLOBAL` - Shared across all users  
- `StateScope.USER` - Per authenticated user across sessions
- `StateScope.RECORD` - Tied to specific database record IDs
- `StateScope.COMPONENT` - Per component instance

**StateConfig parameters:**
- `scope: StateScope` - State scope (default: SESSION)
- `auto_persist: bool` - Enable automatic persistence (default: False)
- `persistence_backend: str` - Backend name ("memory", "database", "redis")
- `ttl: int` - Time-to-live in seconds for cached states

### SSE and Streaming Patterns

- All event responses are SSE streams with proper headers
- **Automatic State Sync**: Always sends `merge_signals` with current state
- **Fragment Updates**: Conditionally sends `merge_fragments` for FastHTML components
- **Streaming Support**: Async generators for real-time streaming responses
- **Merge Modes**: Support for "morph", "inner", "outer", "append", "prepend" via `merge_mode` parameter

### Development Notes

- **No Manual Registration**: States auto-register on first access using class-level `_config`
- **State Access**: Use `MyState.get(req)` for simple, explicit state resolution
- **Smart Defaults**: Classes without `_config` get SESSION scope with no persistence
- **Session Management**: State instances automatically tied to sessions via registry system
- **Parameter Conversion**: Event handlers handle string-to-type conversion from query params
- **Error Handling**: Graceful fallbacks and styled error components using MonsterUI
- **Custom Routing**: Custom routing paths can override default `ClassName/method_name` pattern
- **Clean Architecture**: No dependency injection complexity or monkey patching needed
- **URL Generators**: Automatic static methods for Datastar attributes

### Integration with FastHTML

- **Simple API**: Use `MyState.get(req)` in any FastHTML route handler
- **Auto-registration**: No need for manual `state_registry.register()` calls
- **Event Routes**: `@event` decorated methods are auto-generated as FastHTML routes
- **Backward Compatibility**: Works alongside existing FastHTML patterns
- **Module Structure**: Organized in `app/pages/` directory with automatic route collection
- **Clean Setup**: Minimal configuration required for full functionality

### Real-time Features

- **SSE Endpoint**: `/faststate/sse?states=StateClass1,StateClass2` for subscribing to real-time updates
- **Scope-aware Broadcasting**: Global changes broadcast to all users, session changes only to specific sessions
- **Connection Management**: Automatic cleanup, heartbeat monitoring, and connection pooling
- **Multi-user Collaboration**: Multiple users can interact with shared state in real-time

### Persistence Configuration

- **Memory Backend**: Fast, non-persistent storage for development and caching
- **Database Backend**: SQLAlchemy-based persistence for production use
- **Redis Backend**: High-performance caching with TTL support (requires Redis server)
- **Auto-persist**: Automatically save/load state changes with configurable TTL
- **Backend Management**: Centralized `persistence_manager` for backend configuration

### Production Features

- **Health Monitoring**: Connection statistics and system status via `/status` page
- **Performance Optimization**: Connection pooling, automatic cleanup, and efficient broadcasting
- **Error Handling**: Graceful degradation when backends are unavailable
- **Monitoring Dashboard**: Real-time system stats and SSE connection testing

### Testing Structure

- Tests are standalone Python scripts (no pytest/unittest framework)
- Each test file can be run independently: `python test_<name>.py`
- **test_sse_manager.py**: Tests SSE connection management and broadcasting
- **test_persistence.py**: Tests all persistence backends and TTL functionality
- **test_integration.py**: End-to-end integration tests covering the complete workflow
- **test_registry.py**: Tests state registry functionality and scoping
- **test_fasthtml_integration.py**: Tests FastHTML integration and middleware
- **test_auth.py**: Tests authentication and session handling
- **test_app_integration.py**: Tests demo application integration
- Manual verification required as tests don't use assertion frameworks

### Demo Application Features

The demo app showcases all FastState capabilities with modular page structure:

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

- **Auto-Registration**: States register automatically on first `.get()` call - no manual setup needed
- **State Configuration**: Use `_config = StateConfig(...)` for advanced states, omit for simple ones
- **State Access Pattern**: Use `MyState.get(req, sess, auth)` in route handlers for explicit state resolution
- **State Lifecycle**: States are automatically cached per scope (session, global, user, record)
- **Database File**: Demo app uses SQLite database (`app/faststate_demo.db`) for persistence testing
- **Authentication**: Handled via FastHTML beforeware middleware system
- **Route Collection**: Automatic route discovery from `app/pages/` modules
- **No Complex Setup**: Just import and use - configuration happens automatically
- **Backward Compatibility**: Existing FastHTML patterns work alongside FastState enhancements

## Simple State Access API

```python
# Basic usage in any route (auto-registers with defaults)
my_state = MyState.get(req)

# With explicit session and auth
my_state = MyState.get(req, sess, auth)

# Multiple states in one route
user_profile = UserProfileState.get(req)  # USER scope
settings = GlobalSettingsState.get(req)   # GLOBAL scope  
product = ProductState.get(req)            # RECORD scope (uses record_id from URL)

# Generated URL methods for Datastar
Button("+1", data_on_click=MyState.increment(1))       # → @get('/MyState/increment?amount=1')
Button("Save", data_on_click=ProductState.save())      # → @get('/ProductState/save')
Button("Delete", data_on_click=ProductState.delete(confirm=True))  # → @get('/ProductState/delete?confirm=true')
```

## Configuration Examples

```python
# Default configuration (SESSION scope, no persistence)
class SimpleState(State):
    value: int = 0
    # No _config needed - gets defaults automatically

# Explicit configuration
class AdvancedState(State):
    data: dict = {}
    
    _config = StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="database", 
        ttl=3600  # 1 hour
    )

# Configuration variations
_config = StateConfig(scope=StateScope.USER, auto_persist=True, persistence_backend="redis")
_config = StateConfig(scope=StateScope.RECORD, persistence_backend="memory", ttl=1800)
_config = StateConfig(scope=StateScope.COMPONENT, auto_persist=False)
```