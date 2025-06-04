# FastState

**Simplified Reactive State Management for FastHTML**

A reactive state management system for Python web applications that combines FastHTML and Datastar to enable building interactive UIs entirely in Python - no JavaScript required.

## What is FastState?

FastState introduces a novel approach to web application state management by creating reactive Python classes that automatically synchronize with the frontend via Server-Sent Events (SSE). It bridges the gap between server-side Python logic and client-side reactivity with an elegant, simplified architecture.

### Key Features

- **Pure Python Development**: Build reactive web apps without writing JavaScript
- **Auto-Registration**: States automatically register themselves - no manual setup required
- **Smart Defaults**: Simple states work out-of-the-box with sensible SESSION scope defaults
- **Simplified Configuration**: Single `_config` field for all state configuration when needed
- **Real-time Updates**: Leverages SSE for instant state synchronization between server and client
- **Type Safety**: Built on Pydantic BaseModel for data validation and serialization
- **Automatic Route Generation**: Methods decorated with `@event` become HTTP endpoints with URL generators
- **Two-way Data Binding**: UI changes update server state, server changes update UI instantly
- **Clean Architecture**: ~200 lines of core code vs previous ~400 lines - streamlined and elegant

## How It Works

```python
from faststate import State, event, StateConfig, StateScope

# Simple state with automatic defaults (SESSION scope, no persistence)
class CounterState(State):
    count: int = 0
    
    @event
    def increment(self, amount: int = 1):
        self.count += amount
    
    @event
    def reset(self):
        self.count = 0

# Advanced state with explicit configuration
class GlobalCounterState(State):
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

# In your FastHTML route
@rt('/')
def home(req: Request, sess: dict):
    counter = CounterState.get(req)  # Auto-registers with defaults on first access
    return Main(
        counter,  # Automatically renders with data-signals
        H1("Count: ", Span(data_text="$count")),
        Button("+1", data_on_click=CounterState.increment(1)),  # Generated URL method
        Button("Reset", data_on_click=CounterState.reset())
    )
```

The magic happens through:

1. **Auto-Registration**: States register themselves on first access using class-level configuration or smart defaults
2. **Simple State Access**: Use `MyState.get(req)` to access scoped state instances
3. **Event Decorators**: Methods with `@event` become HTTP endpoints that return SSE streams
4. **URL Generators**: Automatically creates static methods for Datastar attributes (e.g., `MyState.increment(1)` → `@get('/MyState/increment?amount=1')`)
5. **Datastar Integration**: UI elements use `data-*` attributes for binding and event handling
6. **Automatic Updates**: State changes trigger SSE events that update bound UI elements instantly

## Architecture

FastState combines three powerful technologies:

- **FastHTML**: Python-to-HTML framework for server-side rendering and routing
- **Datastar**: Lightweight (~15KB) frontend library for reactivity via SSE
- **Pydantic**: Type-safe data models with validation and serialization

The result is a full-stack reactive framework where:
- State is managed in Python classes with automatic registration
- UI is defined using FastHTML components
- Reactivity is handled by Datastar over SSE
- No custom JavaScript is required
- Configuration is simple and optional

## State Configuration Options

```python
# Default configuration (automatic)
class SimpleState(State):
    value: int = 0
    # Gets SESSION scope, no persistence automatically

# Explicit configuration
class AdvancedState(State):
    data: dict = {}
    
    _config = StateConfig(
        scope=StateScope.GLOBAL,      # GLOBAL, SESSION, USER, RECORD, COMPONENT
        auto_persist=True,             # Enable automatic persistence
        persistence_backend="database", # "memory", "database", "redis"
        ttl=3600                      # Time-to-live in seconds
    )

# Configuration variations
_config = StateConfig(scope=StateScope.USER, auto_persist=True, persistence_backend="redis")
_config = StateConfig(scope=StateScope.RECORD, persistence_backend="memory", ttl=1800)
_config = StateConfig(scope=StateScope.COMPONENT, auto_persist=False)
```

## Current Status

This project has been significantly simplified and refined. Recent improvements:

- **Auto-Registration**: Eliminated manual `state_registry.register()` calls
- **Simplified Configuration**: Single `_config` field instead of multiple separate fields
- **Smart Defaults**: States without configuration get sensible defaults automatically
- **Clean Architecture**: Streamlined from ~400 to ~200 lines of core code
- **Direct Enum Usage**: `StateScope.GLOBAL` instead of string mappings
- **URL Generators**: Automatic static methods for Datastar attributes
- **Production Ready**: Multiple persistence backends, SSE management, health monitoring

## Getting Started

```bash
# Install dependencies
uv sync

# Run the demo application
python app/main.py
```

Visit `http://localhost:5001` to see the interactive demo showcasing:
- **Auto-Registration**: States register automatically on first access
- **Smart Defaults**: Simple states work without configuration
- **Multiple Scopes**: SESSION, GLOBAL, USER, RECORD, COMPONENT examples
- **Real-time Updates**: Live collaboration and state synchronization
- **Persistence**: Database and memory backend examples
- **URL Generators**: Generated methods for Datastar attributes
- **Modular Structure**: Organized page modules with automatic route collection

## Technology Stack

- **FastHTML**: Server-side HTML generation and routing
- **Datastar**: Client-side reactivity and SSE transport (~15KB)
- **Pydantic**: Data validation and serialization
- **MonsterUI**: Styling and UI components
- **UV**: Fast Python package management

## Demo Application Structure

```
app/pages/
├── index.py          # MyState (default SESSION scope)
├── counter.py         # CounterState (GLOBAL scope, memory persistence)
├── admin.py           # GlobalSettingsState (GLOBAL scope, database)
├── auth.py            # UserProfileState (USER scope, database)
├── product.py         # ProductState (RECORD scope, database)
└── chat.py            # ChatState (GLOBAL scope, memory, real-time)
```

## Example Configurations

```python
# Home page - automatic defaults
class MyState(State):
    myInt: int = 0
    myStr: str = "Hello"
    # No _config needed - gets SESSION scope, no persistence

# Global counter with memory persistence
class CounterState(State):
    count: int = 0
    _config = StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="memory",
        ttl=30
    )

# User profile with database persistence
class UserProfileState(State):
    name: str = ""
    email: str = ""
    _config = StateConfig(
        scope=StateScope.USER,
        auto_persist=True,
        persistence_backend="database",
        ttl=3600
    )

# Product records tied to specific IDs
class ProductState(State):
    name: str = ""
    price: float = 0.0
    _config = StateConfig(
        scope=StateScope.RECORD,
        auto_persist=True,
        persistence_backend="database",
        ttl=7200
    )
```

## Research and Development

This project emerged from research into combining FastHTML's server-side approach with modern reactive patterns. See `docs/StateResearch.md` for detailed architectural analysis and design decisions.

The goal is to provide React-like developer experience but with Python on both client and server, leveraging web standards (SSE, HTML) instead of complex JavaScript frameworks.

## License

[License details to be added]

## Contributing

This project is in active development. Contributions, feedback, and ideas are welcome as we continue to refine the architecture and patterns.