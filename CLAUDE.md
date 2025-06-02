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
   - Inherits from SQLModel for data validation and optional persistence
   - Provides simple `.get(req)` class method for explicit state resolution
   - Automatically generates SSE endpoints for decorated methods
   - Handles state synchronization between server and client via Datastar signals
   - Integrated with SSE broadcasting for real-time multi-user updates

2. **Event Decorator System**:
   - `@event` decorator automatically registers methods as HTTP endpoints
   - Supports custom routing paths, HTTP methods, and Datastar selectors
   - Generates SSE responses for real-time state updates
   - Handles parameter conversion from query strings and JSON payloads
   - Automatically broadcasts state changes via SSE manager

3. **State Registry** (`src/faststate/registry.py`):
   - Global registry tracking active state instances with configurable scopes
   - Supports SESSION, GLOBAL, USER, RECORD, and COMPONENT scopes
   - Session-based state retrieval and management via `state_registry.resolve_state_sync()`
   - Automatic state lifecycle management and caching
   - Integrated with persistence layer for automatic state loading/saving
   - Powers the simple `.get()` method for explicit state resolution

4. **SSE Connection Manager** (`src/faststate/sse_manager.py`):
   - Advanced SSE connection management with scope-aware broadcasting
   - Connection pooling and automatic cleanup for production reliability
   - Scope-specific broadcasting (global, session, user, record-based)
   - Health monitoring and connection statistics
   - Heartbeat mechanism and connection expiry handling

5. **Persistence Layer** (`src/faststate/persistence.py`):
   - Multi-backend persistence system (Memory, Redis, Database)
   - Automatic state loading and saving with configurable TTL
   - Pluggable backend architecture for different storage needs
   - Production-ready with SQLAlchemy and Redis support
   - Supports both async and sync operations for flexibility

### Key Patterns

- **State classes** inherit from `State` and define reactive properties
- **Simple state access** via `MyState.get(req)` method for explicit resolution
- **Event methods** use `@event` decorator for automatic route registration
- **UI binding** uses Datastar `data-*` attributes for two-way binding
- **State updates** automatically trigger SSE events to update client signals
- **Session management** ties state instances to user sessions via registry
- **Real-time collaboration** via scope-aware SSE broadcasting
- **Automatic persistence** with configurable backends and TTL
- **Production monitoring** with connection stats and health checks

### Technology Stack

- **FastHTML**: Server-side HTML generation and routing
- **Datastar**: Client-side reactivity and SSE handling
- **SQLModel**: Data validation and optional persistence
- **MonsterUI**: UI component library for styling

### State Management Flow

1. State class defines reactive properties and event handlers
2. Route handlers use `MyState.get(req)` to access state instances
3. UI renders with `data-signals` containing initial state
4. User interactions trigger events via Datastar `data-on-*` attributes
5. Event handlers update state and return SSE responses
6. Client receives SSE updates and automatically updates bound UI elements

### Example State Class Structure

```python
class MyState(State):
    # Reactive properties
    myInt: int = 0
    myStr: str = "Hello"
    
    # Event handlers
    @event
    def increment(self, amount: int):
        self.myInt += amount
    
    @event("/custom-path", method="post")
    def custom_event(self):
        # Custom logic here
        pass

# Enhanced state registration with persistence and scope
state_registry.register(
    MyState,
    StateConfig(
        scope=StateScope.SESSION,
        auto_persist=True,
        persistence_backend="database",
        ttl=3600  # 1 hour cache
    )
)

# Simple route usage with .get() method
@rt('/')
def index(req: Request, sess: dict, auth: str = None):
    my_state = MyState.get(req, sess, auth)  # Explicit, clean state access
    return Titled("My Page", 
        Div(data_signals=json.dumps(my_state.model_dump())),
        my_state  # Renders state UI automatically
    )
```

### SSE and Streaming Patterns

- All event responses are SSE streams
- `_diff_and_events()` method compares before/after state
- Support for async generators for streaming responses
- Fragment merging for dynamic HTML updates

### Development Notes

- **State Access**: Use `MyState.get(req)` for simple, explicit state resolution
- **State Registration**: Register states with `state_registry.register()` for scope and persistence configuration
- **Session Management**: State instances are automatically tied to sessions via registry system
- **Parameter Conversion**: Event handlers handle string-to-type conversion from query params
- **Error Handling**: Returns styled error components using MonsterUI styles
- **Custom Routing**: Custom routing paths can override default `ClassName/method_name` pattern
- **No Monkey Patching**: Clean architecture without FastHTML internal dependencies
- **Demo Application**: `app/main.py` shows all state scopes and `.get()` method usage

### Integration with FastHTML

- **Simple API**: Use `MyState.get(req)` in any FastHTML route handler
- **State Registration**: Register states with `state_registry.register()` for configuration
- **Event Routes**: `@event` decorated methods are auto-generated as FastHTML routes
- **Backward Compatibility**: Works alongside existing FastHTML patterns
- **No Complex Setup**: Just call `initialize_faststate()` during app startup
- **Clean Architecture**: No dependency injection complexity or monkey patching needed

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

The demo app (`app/main.py`) showcases all FastState capabilities:

- **Home (`/`)**: Basic state management with session scope
- **Profile (`/profile`)**: User-scoped state with database persistence
- **Admin (`/admin`)**: Global state management for system settings
- **Products (`/product/{id}`)**: Record-scoped state tied to specific IDs
- **Chat (`/chat`)**: Real-time collaborative chat with global state and SSE
- **Counter (`/counter`)**: Global counter with persistence and multi-user sync
- **Status (`/status`)**: System monitoring dashboard with live statistics

## Important Development Notes

- **State Access Pattern**: Use `MyState.get(req, sess, auth)` in route handlers for explicit state resolution
- **State Lifecycle**: States are automatically cached per scope (session, global, user, record)
- **Database File**: Demo app uses SQLite database (`app/faststate_demo.db`) for persistence testing
- **Authentication**: Handled via FastHTML beforeware middleware system
- **Route Integration**: Legacy routes in `app/routes.py` are merged with auto-generated state routes
- **No Dependency Injection**: Clean, explicit API without complex middleware or patching
- **Backward Compatibility**: Existing FastHTML patterns work alongside FastState enhancements

## Simple State Access API

```python
# Basic usage in any route
my_state = MyState.get(req)

# With explicit session and auth
my_state = MyState.get(req, sess, auth)

# Multiple states in one route
user_profile = UserProfileState.get(req)
settings = GlobalSettingsState.get(req)
product = ProductState.get(req)  # Uses record_id from URL params
```