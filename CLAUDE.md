# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run the application**: `python app/main.py` or `python -m app.main`
- **Install dependencies**: `uv sync` (uses uv for dependency management)
- **Add dependencies**: `uv add <package-name>`
- **Install dev dependencies**: `uv sync --group dev`

## Project Architecture

FastState is a reactive state management system that integrates FastHTML with Datastar for building interactive web applications entirely in Python. The architecture follows these key patterns:

### Core Components

1. **ReactiveState Base Class** (`src/faststate/state.py`): 
   - Inherits from SQLModel for data validation and optional persistence
   - Automatically generates SSE endpoints for decorated methods
   - Handles state synchronization between server and client via Datastar signals

2. **Event Decorator System**:
   - `@event` decorator automatically registers methods as HTTP endpoints
   - Supports custom routing paths, HTTP methods, and Datastar selectors
   - Generates SSE responses for real-time state updates
   - Handles parameter conversion from query strings and JSON payloads

3. **State Registry** (`_STATE_REGISTRY`):
   - Global registry tracking active state instances
   - Session-based state retrieval and management
   - Automatic state lifecycle management

### Key Patterns

- **State classes** inherit from `ReactiveState` and define reactive properties
- **Event methods** use `@event` decorator for automatic route registration
- **UI binding** uses Datastar `data-*` attributes for two-way binding
- **State updates** automatically trigger SSE events to update client signals
- **Session management** ties state instances to user sessions

### Technology Stack

- **FastHTML**: Server-side HTML generation and routing
- **Datastar**: Client-side reactivity and SSE handling
- **SQLModel**: Data validation and optional persistence
- **MonsterUI**: UI component library for styling

### State Management Flow

1. State class defines reactive properties and event handlers
2. UI renders with `data-signals` containing initial state
3. User interactions trigger events via Datastar `data-on-*` attributes
4. Event handlers update state and return SSE responses
5. Client receives SSE updates and automatically updates bound UI elements

### Example State Class Structure

```python
class MyState(ReactiveState):
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
```

### SSE and Streaming Patterns

- All event responses are SSE streams
- `_diff_and_events()` method compares before/after state
- Support for async generators for streaming responses
- Fragment merging for dynamic HTML updates

### Development Notes

- State instances are tied to sessions via `_get_state()` function
- Parameter conversion handles string-to-type conversion from query params
- Error handling returns styled error components
- Custom routing paths can override default `ClassName/method_name` pattern