# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run the application**: `python app/main.py` or `python -m app.main`
- **Install dependencies**: `uv sync` (uses uv for dependency management)
- **Add dependencies**: `uv add <package-name>`
- **Install dev dependencies**: `uv sync --group dev`
- **Run tests**: `python test_<test_name>.py` (tests are standalone scripts)
- **Run all tests**: Execute individual test files directly (no unified test runner configured)

## Project Architecture

StarModel is a reactive state management system that integrates FastHTML with Datastar for building interactive web applications entirely in Python. The architecture has been **significantly simplified** following fast.ai coding standards with clean, short methods (<10 lines each).

### Core Components

1. **State Base Class** (`src/starmodel/state.py`): 
   - **Ultra-Simple API**: Just `MyState.get(req)` for state access (5 lines of code)
   - **Standard Python Patterns**: Uses standard `__init__` method instead of complex factory patterns
   - **Clean Separation**: State creation, client sync, and persistence clearly separated
   - **Signal-based Architecture**: Uses `SignalModelMeta` metaclass for automatic `field_signal` descriptors
   - **StateStore Enumeration**: Simple configuration using `StateStore` enum (CLIENT_SESSION, CLIENT_LOCAL, SERVER_MEMORY, CUSTOM)
   - **Unified Caching**: Uses `memory_persistence` for all caching with proper TTL cleanup
   - **No Recursion Issues**: Fixed infinite recursion between `__init__` and client sync methods

2. **Event Decorator System**:
   - `@event` decorator automatically registers methods as HTTP endpoints
   - **URL Generator Methods**: Automatically creates static methods for Datastar attributes
   - **Parameter Extraction**: Enhanced support for Datastar payload alongside FastHTML parameters
   - **SSE Streaming**: All events return Server-Sent Event streams with state synchronization
   - **Real-time Updates**: Automatic `merge_signals` and optional `merge_fragments`

3. **Simplified Signal System**:
   - **Automatic Field Signals**: Every field gets `MyState.field_signal` descriptor
   - **Clean Namespace Support**: Optional class-based namespacing (`$ClassName.field`)
   - **Direct Signal Access**: Simple `state.signal('fieldname')` method
   - **Datastar Integration**: Seamless integration with Datastar's reactive system

4. **Unified Persistence Layer** (`src/starmodel/persistence.py`):
   - **Single Backend**: `MemoryStatePersistence` serves as unified cache and persistence
   - **Instance Storage**: Stores whole State instances (not serialized data) for efficiency
   - **TTL Support**: Built-in expiration with cleanup via `save(ttl=X)` parameter
   - **Simple API**: Just `save()`, `delete()`, and `exists()` methods

### Key Architectural Improvements

#### **Simplified State.get() Method** (5 lines):
```python
@classmethod
def get(cls, req: Request, **kwargs) -> 'State':
    """Get cached state or create new."""
    state_id = cls._get_id(req, **kwargs)
    cached = memory_persistence._data.get(state_id)
    if cached and isinstance(cached, cls):
        return cached
    return cls(req, id=state_id, **kwargs)
```

#### **Standard Python __init__** (6 lines):
```python
def __init__(self, req: Request = None, **kwargs):
    super().__init__(**kwargs)
    if not self.id:
        self.id = self._get_id(req, **kwargs)
    self._sync_from_client(req)  # Sync BEFORE caching
    self._cache_self()           # Cache the synced state
    if self.auto_persist:
        self.save()
```

#### **Clean Helper Methods** (each <10 lines):
- `_get_id()` - Simple ID generation (overridable)
- `_sync_from_client()` - Client sync without recursion
- `_cache_self()` - Instance caching
- `save(ttl=None)` - Persistence with optional TTL override

### Technology Stack

- **FastHTML**: Server-side HTML generation and routing
- **Datastar**: Client-side reactivity and SSE handling (~15KB)
- **Pydantic**: Data validation and serialization (BaseModel)
- **MonsterUI**: UI component library for styling

### State Management Flow

1. **Simple State Access**: `MyState.get(req)` - auto-caches with memory persistence
2. **Standard Creation**: Uses Python `__init__` patterns users expect  
3. **Client Sync**: Automatic sync with Datastar payload on state access
4. **Instance Caching**: Whole objects cached (not serialized) for performance
5. **Event Handling**: `@event` methods trigger SSE responses with state updates
6. **Automatic Persistence**: Configurable persistence with TTL support

### Current Configuration System

#### **Simple model_config**:
```python
class MyState(State):
    # Default config - no setup needed
    myInt: int = 0
    myStr: str = "Hello from StarModel"

class AdvancedState(State):
    data: dict = {}
    
    model_config = {
        "store": StateStore.CLIENT_SESSION,      # Where to store
        "auto_persist": True,                    # Auto-save changes
        "persistence_backend": memory_persistence, # How to store
        "sync_with_client": True,               # Client sync
        "use_namespace": True,                  # Namespaced signals
    }
```

#### **StateStore Options**:
- `StateStore.SERVER_MEMORY` - Server-side memory persistence (default)
- `StateStore.CLIENT_SESSION` - Browser sessionStorage (Datastar managed)
- `StateStore.CLIENT_LOCAL` - Browser localStorage (Datastar managed)  
- `StateStore.CUSTOM` - Custom persistence backend

### Demo Application Structure

The demo showcases StarModel capabilities with clean, modular pages:

- **Home (`/`)**: MyState with default configuration
- **Counter (`/counter`)**: Enhanced counter with real-time streaming
- **Dashboard (`/dashboard`)**: Complex state with computed fields and charts
- **Admin (`/admin`)**: Global settings with system monitoring
- **Auth (`/auth-demo`)**: User profiles with authentication
- **Chat (`/chat`)**: Real-time collaboration demo
- **Product (`/product/{id}`)**: Record-scoped state tied to IDs

### Page Module Structure
```
app/pages/
├── __init__.py
├── index.py          # MyState (session-scoped)
├── counter.py         # CounterState (enhanced with streaming)
├── dashboard.py       # DashboardState (computed fields, charts)
├── admin.py           # GlobalSettingsState (global scope)
├── auth.py            # UserProfileState (user-scoped)
├── product.py         # ProductState (record-scoped)
├── chat.py            # ChatState (real-time collaboration)
└── templates.py       # Shared page templates
```

## Development Patterns

### **State Access Pattern** (Recommended):
```python
@rt('/')
def index(req: Request):
    my_state = MyState.get(req)  # Simple, explicit state resolution
    return Main(
        my_state,  # Auto-renders with signals and persistence
        Button("+1", data_on_click=MyState.increment(1)),  # URL generator
        P(f"Count: {my_state.myInt}")  # Direct value access
    )
```

### **Event Methods**:
```python
class CounterState(State):
    count: int = 0
    
    @event  # Default GET endpoint
    def increment(self, amount: int = 1):
        self.count += amount
    
    @event(method="post", selector="#counter")  # Custom config
    def reset(self):
        self.count = 0
        return Div(f"Reset to {self.count}", id="counter")
```

### **Signal Usage**:
```python
# In Python code
Span(data_text=MyState.count_signal)  # → data-text="$count" or "$MyState.count"

# Direct signal access
my_state.signal('count')  # Returns "$count" or "$MyState.count"
```

## Important Development Notes

- **Fast.ai Standards**: All methods kept under 10 lines following fast.ai guidelines
- **No Recursion**: Fixed infinite recursion issues between `__init__` and client sync
- **Instance Caching**: Stores whole State objects for performance (not serialized data)
- **Standard Python**: Uses familiar `__init__` patterns instead of complex factories
- **Clean Separation**: State creation, sync, caching, and persistence clearly separated
- **Extensibility**: Easy to override `_get_id()` or other helper methods for custom logic
- **Error Prevention**: Sync happens before caching to avoid stale data
- **Repository**: Now uses `main` branch as default with clean Git setup
- **Project Name**: Fully renamed from FastState to StarModel throughout codebase

## Simple State Access API

```python
# Basic usage (auto-caches, session-scoped by default)
my_state = MyState.get(req)

# Multiple states in one route  
counter = CounterState.get(req)     # SERVER_MEMORY store
profile = SessionState.get(req)     # CLIENT_SESSION store

# Generated URL methods for Datastar
Button("+1", data_on_click=MyState.increment(1))
Input(data_bind=MyState.text_signal, data_on_change=MyState.update_text())

# Signal access for reactive binding
Div("Count:", Span(data_text=MyState.count_signal))
```

## Configuration Examples

```python
# Minimal configuration (uses all defaults)
class SimpleState(State):
    value: int = 0
    
    @event
    def increment(self):
        self.value += 1

# Client-side storage
class ClientState(State):
    data: dict = {}
    
    model_config = {
        "store": StateStore.CLIENT_SESSION,  # sessionStorage
        "auto_persist": False,               # Disable server persistence
    }

# Advanced server-side configuration  
class PersistentState(State):
    important_data: str = ""
    
    model_config = {
        "store": StateStore.SERVER_MEMORY,
        "auto_persist": True,
        "persistence_backend": memory_persistence,
        "use_namespace": True,
        "sync_with_client": True,
    }
    
    def save(self, ttl=3600):  # Custom TTL
        return super().save(ttl)
```

## Recent Major Improvements

1. **Simplified Architecture**: Reduced `State.get()` from 60+ lines to 5 lines
2. **Fixed Recursion**: Eliminated infinite recursion between `__init__` and client sync
3. **Instance Caching**: Store whole objects instead of serialized data for performance
4. **Standard Patterns**: Use familiar Python `__init__` instead of complex factories
5. **Clean Separation**: Clear separation between creation, sync, caching, and persistence
6. **Fast.ai Standards**: All methods under 10 lines following coding best practices
7. **Complete Rename**: Project fully renamed from FastState to StarModel
8. **Git Cleanup**: Main branch as default, clean repository structure

The StarModel project now provides a radically simplified, high-performance state management system for FastHTML applications while maintaining full functionality and extensibility.