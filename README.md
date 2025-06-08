# BackState 🚧 (Under testing)

**Simplified Reactive State Management for FastHTML**

A reactive state management system for Python web applications that combines FastHTML and Datastar to enable building interactive UIs entirely in Python - no JavaScript required.

## What is BackState?

BackState makes building reactive web applications incredibly simple by creating Python classes that automatically synchronize with the frontend via Server-Sent Events (SSE). It bridges the gap between server-side Python logic and client-side reactivity with an elegant, streamlined architecture.

### Key Features

- **Pure Python Development**: Build reactive web apps without writing JavaScript
- **Signal-Based Architecture**: Automatic reactive bindings for all model fields 
- **Smart Defaults**: States work out-of-the-box with SERVER_MEMORY storage and auto-persistence
- **Simple Configuration**: Use Pydantic's `model_config` for customization when needed
- **Real-time Updates**: Leverages SSE for instant state synchronization between server and client
- **Type Safety**: Built on Pydantic BaseModel for data validation and serialization
- **Automatic Route Generation**: Methods decorated with `@event` become HTTP endpoints with URL generators
- **Client-side Storage**: Support for sessionStorage and localStorage via Datastar
- **Clean Architecture**: Streamlined codebase with automatic signal descriptors and route registration

## Installation

```bash
# Clone the repository
git clone https://github.com/ndendic/BackState.git
cd BackState

# Install dependencies using uv
uv sync

# Run the demo application
python app/main.py
```

Visit `http://localhost:5001` to see the interactive demo!

## Quick Start

```python
from faststate import State, event, StateStore

# Simple state with automatic defaults (SERVER_MEMORY store, auto-persist enabled)
class CounterState(State):
    count: int = 0
    
    @event
    def increment(self, amount: int = 1):
        self.count += amount
    
    @event
    def reset(self):
        self.count = 0

# State with client-side persistence
class SessionState(State):
    name: str = ""
    preferences: dict = {}
    
    model_config = {
        "store": StateStore.CLIENT_SESSION,  # Use sessionStorage
        "use_namespace": True,               # Enable namespaced signals
        "auto_persist": False                # Client storage doesn't need server persistence
    }
    
    @event
    def update_name(self, name: str):
        self.name = name

# In your FastHTML route
@rt('/')
def home(req: Request):
    counter = CounterState.get(req)  # Auto-caches with memory persistence
    session = SessionState.get(req)  # Auto-syncs with sessionStorage
    
    return Main(
        counter,  # Automatically renders with data-signals
        H1("Count: ", Span(data_text=counter.count_signal)),  # → data-text="$CounterState.count"
        Button("+1", data_on_click=CounterState.increment(1)),  # Generated URL method
        Button("Reset", data_on_click=CounterState.reset()),
        Hr(),
        Input(placeholder="Your name", data_model=session.name_signal),  # Two-way binding
        P(f"Hello, {session.name}!" if session.name else "Enter your name above")
    )
```

## FastHTML Integration

Setting up BackState with your FastHTML app is simple:

```python
from fasthtml.common import *
from faststate import datastar_script, states_rt

# Create your FastHTML app
app, rt = fast_app(
    live=True,
    hdrs=(
        datastar_script,  # Include Datastar for reactivity
    ),
)

# Add your page routes
@rt('/')
def home(req: Request):
    return Main(H1("Welcome to BackState!"))

# Add BackState routes (automatically registers @event methods)
states_rt.to_app(app)

if __name__ == "__main__":
    serve()
```

## How It Works

The magic happens through:

1. **Signal System**: Every Pydantic field automatically gets a signal descriptor (e.g., `count_signal` → `$ClassName.count`)
2. **Simple State Access**: Use `MyState.get(req)` to access cached state instances
3. **Event Decorators**: Methods with `@event` become HTTP endpoints that return SSE streams
4. **URL Generators**: Automatically creates static methods for Datastar attributes (e.g., `MyState.increment(1)` → `@get('/MyState/increment?amount=1')`)
5. **Datastar Integration**: UI elements use `data-*` attributes for binding and event handling
6. **Automatic Updates**: State changes trigger SSE events that update bound UI elements instantly

## Architecture

BackState combines three powerful technologies:

- **FastHTML**: Python-to-HTML framework for server-side rendering and routing
- **Datastar**: Lightweight (~15KB) frontend library for reactivity via SSE
- **Pydantic**: Type-safe data models with validation and serialization

The result is a full-stack reactive framework where:
- State is managed in Python classes with automatic signal generation
- UI is defined using FastHTML components with reactive data binding
- Reactivity is handled by Datastar over SSE
- No custom JavaScript is required
- Configuration uses standard Pydantic patterns

## State Configuration Options

```python
from faststate import State, StateStore, memory_persistence

# Default configuration (SERVER_MEMORY store, auto_persist enabled)
class SimpleState(State):
    value: int = 0
    # No model_config needed - gets smart defaults

# Client-side sessionStorage
class SessionState(State):
    user_preferences: dict = {}
    
    model_config = {
        "store": StateStore.CLIENT_SESSION,  # Browser sessionStorage
        "use_namespace": True,               # Namespaced signals
        "auto_persist": False                # Datastar handles persistence
    }

# Client-side localStorage
class LocalState(State):
    app_settings: dict = {}
    
    model_config = {
        "store": StateStore.CLIENT_LOCAL,    # Browser localStorage
        "use_namespace": False,              # Global signals
        "sync_with_client": True             # Sync with client changes
    }

# Server-side with custom persistence
class PersistentState(State):
    important_data: str = ""
    
    model_config = {
        "store": StateStore.SERVER_MEMORY,
        "auto_persist": True,
        "persistence_backend": memory_persistence,  # Custom backend
        "namespace": "MyCustomNamespace"            # Custom namespace
    }
```

## Real-time Features

BackState includes powerful real-time capabilities:

```python
class LiveCounter(State):
    count: int = 0
    
    @event
    async def live_updates(self, heartbeat: float = 1.0):
        """Stream live updates every heartbeat seconds"""
        while True:
            yield f"Current count: {self.count}"
            await asyncio.sleep(heartbeat)
    
    @event
    async def poll_for_changes(self):
        """Polling endpoint for state updates"""
        pass  # Just returns current state
    
    @event 
    async def sync_with_client(self, datastar):
        """Sync server state with client changes"""
        self.set_from_request(datastar)

# Built-in helper components
def live_counter_ui(counter: LiveCounter):
    return Div(
        counter.PollDiv(heartbeat=2.0),    # Polls every 2 seconds
        counter.PullSyncDiv(),             # Syncs when page comes online
        H1(f"Count: {counter.count}"),
        Button("+1", data_on_click=counter.increment(1))
    )
```

## Easy Interactive Examples

### Todo List with Real-time Updates

```python
class TodoState(State):
    items: list[str] = []
    
    @event
    def add_item(self, item: str):
        if item.strip():
            self.items.append(item.strip())
    
    @event
    def remove_item(self, index: int):
        if 0 <= index < len(self.items):
            self.items.pop(index)

@rt('/todos')
def todos_page(req: Request):
    todos = TodoState.get(req)
    
    return Main(
        todos,  # Renders with data-signals
        H1("My Todo List"),
        Form(
            Input(placeholder="Add new todo...", name="item"),
            Button("Add", data_on_click=todos.add_item("$item")),
        ),
        Ul(*[
            Li(
                item,
                Button("×", data_on_click=todos.remove_item(i))
            ) for i, item in enumerate(todos.items)
        ], data_text="$TodoState.items")  # Auto-updates when items change
    )
```

### Chat Application

```python
class ChatState(State):
    messages: list[dict] = []
    
    model_config = {
        "store": StateStore.SERVER_MEMORY,  # Shared across all users
        "use_namespace": True
    }
    
    @event
    def send_message(self, message: str, user: str = "Anonymous"):
        if message.strip():
            self.messages.append({
                "user": user,
                "message": message.strip(),
                "timestamp": time.time()
            })

@rt('/chat')
def chat_page(req: Request):
    chat = ChatState.get(req)
    
    return Main(
        chat,
        H1("Live Chat"),
        Div(
            *[Div(f"{msg['user']}: {msg['message']}") for msg in chat.messages],
            data_text="$ChatState.messages",  # Real-time message updates
            style="height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px;"
        ),
        Form(
            Input(placeholder="Type a message...", name="message"),
            Input(placeholder="Your name", name="user", value="Anonymous"),
            Button("Send", data_on_click=chat.send_message("$message", "$user"))
        )
    )
```

## Why BackState Makes FastHTML + Datastar Easy

BackState eliminates the complexity of integrating FastHTML with Datastar by providing:

### 🔧 **Zero Configuration**
```python
# Just inherit from State - that's it!
class MyState(State):
    count: int = 0
    
    @event
    def increment(self):
        self.count += 1
```

### 🎯 **Automatic Signal Generation**
```python
# Every field automatically gets reactive signals
my_state.count_signal        # → "$MyState.count"
Span(data_text=my_state.count_signal)  # Reactive binding
```

### 🔗 **Generated URL Methods**
```python
# Event methods become Datastar-compatible URLs
Button("+1", data_on_click=MyState.increment())  # → "@get('/MyState/increment')"
```

### 📦 **Built-in Persistence**
```python
# Choose your storage with one line
model_config = {"store": StateStore.CLIENT_SESSION}  # sessionStorage
model_config = {"store": StateStore.SERVER_MEMORY}   # Server memory (default)
```

### ⚡ **Real-time by Default**
```python
# All @event methods return SSE streams automatically
@event
def update_data(self):
    self.data = "new value"  # Instantly updates all connected clients
```

## Technology Stack

- **FastHTML**: Server-side HTML generation and routing
- **Datastar**: Client-side reactivity and SSE transport (~15KB)
- **Pydantic**: Data validation and serialization  
- **UV**: Fast Python package management

## Demo Application

The included demo app (`python app/main.py`) showcases:

- **Home Page**: Simple counter with session-based state
- **Counter**: Global shared counter with memory persistence
- **Chat**: Real-time multi-user chat application
- **Templates**: Form handling with client-side storage
- **Authentication**: Session management integration

Visit the different pages to see how easy it is to build reactive web apps entirely in Python!

## Research and Development

BackState emerged from research into combining FastHTML's server-side approach with modern reactive patterns. The goal is to provide a React-like developer experience using only Python, leveraging web standards (SSE, HTML) instead of complex JavaScript frameworks.

## Contributing

This project is in active development. Contributions, feedback, and ideas are welcome as we continue to refine the architecture and patterns. Feel free to:

- Report issues or bugs
- Suggest new features  
- Contribute examples
- Improve documentation
- Share your BackState applications

## License

MIT License - see LICENSE file for details.