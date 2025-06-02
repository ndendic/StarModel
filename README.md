# FastState

**Work in Progress**

A reactive state management system for Python web applications that combines FastHTML and Datastar to enable building interactive UIs entirely in Python - no JavaScript required.

## What is FastState?

FastState introduces a novel approach to web application state management by creating reactive Python classes that automatically synchronize with the frontend via Server-Sent Events (SSE). It bridges the gap between server-side Python logic and client-side reactivity.

### Key Features

- **Pure Python Development**: Build reactive web apps without writing JavaScript
- **Declarative State Management**: Define state as Python classes with automatic UI synchronization
- **Real-time Updates**: Leverages SSE for instant state synchronization between server and client
- **Type Safety**: Built on Pydantic/SQLModel for data validation and optional persistence
- **Automatic Route Generation**: Methods decorated with `@event` become HTTP endpoints automatically
- **Two-way Data Binding**: UI changes update server state, server changes update UI instantly

## How It Works

```python
from faststate import State, event

class CounterState(State):
    count: int = 0
    
    @event
    def increment(self, amount: int = 1):
        self.count += amount
    
    @event
    def reset(self):
        self.count = 0

# In your FastHTML route
@rt('/')
def home(req: Request, sess: dict):
    counter = CounterState.get(req)  # Simple, explicit state access
    return Titled("Counter App",
        Div(
            H1("Count: ", Span(data_text="$count")),
            Button("+", data_on_click=CounterState.increment(1)),
            Button("Reset", data_on_click=CounterState.reset()),
            data_signals=json.dumps(counter.model_dump())
        )
    )
```

The magic happens through:

1. **Reactive State Classes**: Inherit from `State` to get automatic state synchronization
2. **Simple State Access**: Use `MyState.get(req)` to access scoped state instances
3. **Event Decorators**: Methods with `@event` become HTTP endpoints that return SSE streams
4. **Datastar Integration**: UI elements use `data-*` attributes for binding and event handling
5. **Automatic Updates**: State changes trigger SSE events that update bound UI elements instantly

## Architecture

FastState combines three powerful technologies:

- **FastHTML**: Python-to-HTML framework for server-side rendering and routing
- **Datastar**: Lightweight (~15KB) frontend library for reactivity via SSE
- **SQLModel**: Type-safe data models with optional database persistence

The result is a full-stack reactive framework where:
- State is managed in Python classes
- UI is defined using FastHTML components
- Reactivity is handled by Datastar over SSE
- No custom JavaScript is required

## Current Status

This project is actively being developed and refined. Current focus areas:

- Core reactive state system
- Event decorator and automatic route generation
- SSE-based state synchronization
- Parameter conversion and validation
- Session-based state management
- Advanced streaming patterns
- Performance optimizations
- Documentation and examples
- Testing framework integration
- Production deployment patterns

## Getting Started

```bash
# Install dependencies
uv sync

# Run the demo application
python app/main.py
```

Visit `http://localhost:5001` to see the interactive demo showcasing:
- Simple `.get()` state access pattern
- Counter with increment/decrement
- Real-time streaming updates
- Two-way data binding  
- State persistence across sessions
- Multiple state scopes (session, global, user, record)

## Technology Stack

- **FastHTML**: Server-side HTML generation and routing
- **Datastar**: Client-side reactivity and SSE transport
- **SQLModel**: Data validation and optional persistence
- **MonsterUI**: Styling and UI components
- **UV**: Fast Python package management

## Research and Development

This project emerged from research into combining FastHTML's server-side approach with modern reactive patterns. See `docs/StateResearch.md` for detailed architectural analysis and design decisions.

The goal is to provide React-like developer experience but with Python on both client and server, leveraging web standards (SSE, HTML) instead of complex JavaScript frameworks.

## License

[License details to be added]

## Contributing

This project is in early development. Contributions, feedback, and ideas are welcome as we refine the architecture and patterns.