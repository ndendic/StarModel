# StarModel

**Entity-Centric Reactive Development for FastHTML**

StarModel enables you to define your application's data structure and behavior in one place, minimizing configuration overhead and maximizing development speed. Build reactive web applications entirely in Python by encapsulating both backend logic and frontend interactivity around your entities.

## Core Philosophy

**Stop separating your data from your behavior.** StarModel brings entity-driven development to web applications:

- **State Models** - Define your data structure and business logic in unified Python classes
- **Event Decorators** - Turn methods into interactive endpoints with zero configuration  
- **Datastar Integration** - Automatic frontend reactivity without writing JavaScript

## Quick Start

```bash
git clone https://github.com/ndendic/StarModel.git
cd StarModel
uv sync
python app/main.py  # Visit http://localhost:5001
```

## Entity-Centric Development

```python
from starmodel import State, event

# Define your entity - data + behavior in one place
class TodoList(State):
    items: list[str] = []
    completed: list[bool] = []
    
    @event
    def add_item(self, text: str):
        self.items.append(text)
        self.completed.append(False)
    
    @event  
    def toggle_item(self, index: int):
        if 0 <= index < len(self.completed):
            self.completed[index] = not self.completed[index]

# Use in FastHTML routes
@rt('/todos')
def todos_page(req: Request):
    todos = TodoList.get(req)  # Auto-persisted per session
    
    return Main(
        todos,  # Renders with reactive data-signals
        H1("My Todos"),
        
        # Interactive UI with zero JavaScript
        Input(placeholder="Add todo...", data_model="$new_item"),
        Button("Add", data_on_click=todos.add_item("$new_item")),
        
        # Reactive list updates automatically  
        Ul(*[
            Li(
                item,
                Button("✓" if completed else "○", 
                      data_on_click=todos.toggle_item(i))
            ) for i, (item, completed) in enumerate(zip(todos.items, todos.completed))
        ])
    )
```

## Why This Matters

### 🎯 **Entity-Driven Architecture**
Your `User`, `Product`, `Order` entities contain both data schema and business logic. No more scattering behavior across controllers, services, and frontend code.

### ⚡ **Zero Configuration Reactivity**  
The `@event` decorator automatically creates HTTP endpoints and generates Datastar-compatible URLs. Your methods become interactive without routing setup.

### 🔄 **Seamless State Synchronization**
Changes to your Python objects instantly update the frontend via Server-Sent Events. Two-way data binding works automatically.

### 📦 **Minimal Peripheral Setup**
No Redux stores, no API layer design, no frontend state management. Just define your entities and interact with them.

## FastHTML Integration

```python
from fasthtml.common import *
from starmodel import datastar_script, states_rt

app, rt = fast_app(hdrs=(datastar_script,))

# Your page routes
@rt('/')  
def home(req: Request):
    return Main(H1("Welcome!"))

# Auto-register all @event methods
states_rt.to_app(app)
```

## Storage Options

```python
from starmodel import StateStore

class UserProfile(State):
    name: str = ""
    preferences: dict = {}
    
    # Choose your persistence layer
    model_config = {
        "store": StateStore.CLIENT_SESSION,  # Browser sessionStorage
        # "store": StateStore.SERVER_MEMORY,  # Server memory (default)  
        # "store": StateStore.CLIENT_LOCAL,   # Browser localStorage
    }
```

## Real-time Collaboration

```python
class ChatRoom(State):
    messages: list[dict] = []
    
    model_config = {"store": StateStore.SERVER_MEMORY}  # Shared across users
    
    @event
    def send_message(self, text: str, username: str):
        self.messages.append({"text": text, "user": username, "time": time.time()})
        # All connected clients update automatically via SSE
```

## Technology Stack

- **FastHTML** - Server-side HTML generation and routing
- **Datastar** - Lightweight (~15KB) frontend reactivity via SSE  
- **Pydantic** - Type-safe data models with validation

## Demo Application

Run `python app/main.py` to see examples of:
- Session-based counters
- Real-time chat 
- Form handling with client storage
- Multi-user collaboration

## Contributing

This project focuses on eliminating the complexity of modern web development by returning to entity-centric design patterns. Contributions welcome!

## License

MIT License