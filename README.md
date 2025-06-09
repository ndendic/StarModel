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

or install package like

```bash
pip install git+https://github.com/ndendic/StarModel.git
```

## Entity-Centric Development

Below is full example you can run (uses MonsterUI for styling)
```python
from fasthtml.common import *
from monsterui.all import *
from starmodel import *

app, rt = fast_app(
    htmx=False,
    hdrs=(
        Theme.zinc.headers(),
        datastar_script,
    ),
)

class Counter(State):
    count: int = 0
    update_count: int = 0
    
    @event
    def increment(self, amount: int = 1):
        self.count += amount
        self.update_count += 1

    @event
    def decrement(self, amount: int = 1):
        self.count -= amount
        self.update_count += 1

    @event
    def reset(self):
        self.count = 0
        self.update_count += 1

@rt
def index(req: Request):
    counter = Counter.get(req)
    return Main(
        counter,
        H1("🔢 Counter Demo"),
        # Counter display
        Card(
            Div(
                Span(data_text=Counter.count_signal, cls=TextT.primary + "text-7xl font-bold"),
                cls="text-center mb-2"
            ),
            Div("Total updates: ", Span(data_text=Counter.update_count_signal), cls=TextT.primary),
            cls=CardT.default + "text-center my-6",
        ),            
        # Counter controls
        Div(
            Div(
                Button("-10", data_on_click=Counter.decrement(10), cls=ButtonT.secondary),
                Button("-1", data_on_click=Counter.decrement(1), cls=ButtonT.secondary),
                Button("Reset", data_on_click=Counter.reset(), cls=ButtonT.secondary),
                Button("+1", data_on_click=Counter.increment(1), cls=ButtonT.secondary),
                Button("+10", data_on_click=Counter.increment(10), cls=ButtonT.secondary),
                cls="text-center mb-6 flex gap-2 justify-center"
            ),
            cls="mb-6"
        ),
        # Custom increment
        Div(
            Form(
                Input(name="amount", type="number", value="1", data_bind="$amount",cls="w-24"),
                Button("+", type="submit", cls=ButtonT.secondary),
                data_on_submit=Counter.increment(),
                cls="mb-6"
            ),
            cls="text-center mb-6"
        ),
        cls="container mx-auto p-8 max-w-3xl"
    )

# Import and add state routes
states_rt.to_app(app)

if __name__ == "__main__":
    serve(reload=True, port=8080)
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