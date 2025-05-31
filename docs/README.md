# FastState Documentation

Welcome to the comprehensive documentation for FastState - a reactive state management system for FastHTML applications.

## 📚 Documentation Overview

FastState provides automatic dependency injection, real-time state synchronization, and clean separation of concerns for building reactive web applications with FastHTML and Datastar.

### 🚀 Getting Started

- **[Quick Start Guide](#quick-start)** - Get up and running in 5 minutes
- **[Installation](#installation)** - Setup instructions and requirements

### 📖 Core Documentation

1. **[Architecture Overview](ArchitectureOverview.md)** 📐
   - High-level system architecture
   - Component interaction flow
   - Design principles and philosophy
   - Data flow and SSE integration

2. **[Core Components](CoreComponents.md)** 🔧
   - ReactiveState base class internals
   - State registry system
   - FastHTML integration layer
   - Event decorator system
   - SSE response generation

3. **[Developer Guide](DeveloperGuide.md)** 👨‍💻
   - Step-by-step implementation guide
   - State scopes and configuration
   - Authentication integration patterns
   - Advanced usage patterns
   - Performance optimization
   - Testing strategies
   - Troubleshooting guide

4. **[API Reference](APIReference.md)** 📋
   - Complete API documentation
   - Class and method references
   - Configuration options
   - Type annotations
   - Error handling
   - Best practices

5. **[Examples and Patterns](ExamplesAndPatterns.md)** 💡
   - Complete application examples
   - Common UI patterns
   - Data management patterns
   - Real-time features
   - Performance patterns

### 📑 Legacy Documentation

- **[State Research](StateResearch.md)** - Original research and design concepts
- **[State Management Requirements](StateManagementRequirements.md)** - Technical requirements
- **[Technical Implementation Guide](TechnicalImplementationGuide.md)** - Implementation phases

---

## Quick Start

### Installation

```bash
# Install core dependencies
pip install fasthtml datastar-py sqlmodel

# Or with uv
uv add fasthtml datastar-py sqlmodel
```

### Basic Setup

```python
from fasthtml.common import *
from faststate import (
    ReactiveState, event, StateScope, StateConfig, 
    state_registry, initialize_faststate
)
import json

# 1. Initialize FastState
initialize_faststate()

# 2. Define your state
class CounterState(ReactiveState):
    count: int = 0
    message: str = "Hello FastState!"
    
    @event
    def increment(self, amount: int = 1):
        self.count += amount
    
    @event
    def reset(self):
        self.count = 0
        self.message = "Reset!"

# 3. Register state
state_registry.register(
    CounterState,
    StateConfig(scope=StateScope.SESSION)
)

# 4. Create FastHTML app
app, rt = fast_app()

# 5. Create routes with automatic state injection
@rt('/')
def home(counter: CounterState):
    return Titled("FastState Demo",
        Div(
            H1("Counter Demo"),
            P(f"Count: {counter.count}"),
            P(counter.message),
            
            Button("Increment", onclick="increment({amount: 1})"),
            Button("Reset", onclick="reset()"),
            
            data_signals=json.dumps(counter.model_dump()),
            id="updates"
        )
    )

# 6. Run your app
if __name__ == "__main__":
    serve(reload=True)
```

---

## 🏗️ Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastHTML Application                    │
├─────────────────────────────────────────────────────────────────┤
│                    FastHTML Beforeware                         │
│                   (Authentication)                             │
├─────────────────────────────────────────────────────────────────┤
│                FastState Integration Layer                     │
│              (Monkey Patch + DI Extension)                     │
├─────────────────────────────────────────────────────────────────┤
│     Route Handler     │    State Registry    │   SSE Events    │
│   (Auto Injection)   │   (Scope Management) │ (Real-time UI)  │
├─────────────────────────────────────────────────────────────────┤
│                    ReactiveState Classes                       │
│              (Business Logic + Event Handlers)                 │
├─────────────────────────────────────────────────────────────────┤
│                    SQLModel/Pydantic                          │
│                (Data Validation + Persistence)                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Key Features

### ✅ Zero Configuration Dependency Injection
```python
@rt('/dashboard')
def dashboard(user: UserState, cart: CartState, settings: AppSettings):
    # All states automatically injected based on type annotations
    return render_dashboard(user, cart, settings)
```

### ✅ Multiple State Scopes
```python
# Session-scoped (per user session)
state_registry.register(ShoppingCart, StateConfig(scope=StateScope.SESSION))

# User-scoped (across sessions for authenticated users)  
state_registry.register(UserProfile, StateConfig(scope=StateScope.USER))

# Global (shared across all users)
state_registry.register(AppSettings, StateConfig(scope=StateScope.GLOBAL))

# Record-scoped (tied to database records)
state_registry.register(DocumentEditor, StateConfig(scope=StateScope.RECORD))
```

### ✅ Automatic SSE Updates
```python
class MyState(ReactiveState):
    count: int = 0
    
    @event  # Automatically creates /MyState/increment endpoint
    def increment(self, amount: int):
        self.count += amount
        # SSE response automatically generated with state diff
```

### ✅ FastHTML Integration
```python
# Uses FastHTML's standard beforeware for authentication
def auth_beforeware(req, sess):
    return sess.get('user_id')

app, rt = fast_app(before=auth_beforeware)
```

### ✅ Type Safety and Validation
```python
class UserState(ReactiveState):
    name: str = ""
    email: EmailStr = ""  # Pydantic validation
    age: int = Field(ge=0, le=150)  # Field validation
    preferences: dict = Field(default_factory=dict)
```

---

## 📖 Documentation Roadmap

### For Beginners
1. Start with **[Quick Start](#quick-start)** above
2. Read **[Developer Guide](DeveloperGuide.md)** sections 1-3
3. Try the examples in **[Examples and Patterns](ExamplesAndPatterns.md)**

### For Advanced Users
1. Study **[Architecture Overview](ArchitectureOverview.md)** for system design
2. Reference **[Core Components](CoreComponents.md)** for internals
3. Use **[API Reference](APIReference.md)** for detailed documentation

### For Contributors
1. Read **[State Research](StateResearch.md)** for background
2. Review **[Technical Implementation Guide](TechnicalImplementationGuide.md)**
3. Check **[State Management Requirements](StateManagementRequirements.md)**

---

## 🔍 Common Use Cases

| Use Case | State Scope | Example |
|----------|-------------|---------|
| Shopping Cart | SESSION | `StateConfig(scope=StateScope.SESSION)` |
| User Profile | USER | `StateConfig(scope=StateScope.USER)` |
| System Settings | GLOBAL | `StateConfig(scope=StateScope.GLOBAL)` |
| Document Editor | RECORD | `StateConfig(scope=StateScope.RECORD)` |
| Widget State | COMPONENT | `StateConfig(scope=StateScope.COMPONENT)` |

## 🛠️ Development Workflow

```python
# 1. Define state class
class MyFeatureState(ReactiveState):
    # Add your fields with type hints
    data: str = ""
    
    @event
    def update_data(self, new_data: str):
        self.data = new_data

# 2. Register with appropriate scope
state_registry.register(
    MyFeatureState,
    StateConfig(scope=StateScope.SESSION)
)

# 3. Use in routes with automatic injection
@rt('/my-feature')
def my_feature_page(feature: MyFeatureState):
    return Titled("My Feature", feature)

# 4. Test your implementation
# See Developer Guide for testing patterns
```

---

## 🤝 Contributing

FastState is designed to be simple, powerful, and extensible. When contributing:

1. **Read the architecture docs** to understand the system
2. **Follow the patterns** shown in examples
3. **Test thoroughly** using the testing patterns
4. **Document your changes** following the existing style

---

## 📞 Support and Resources

- **[GitHub Issues](https://github.com/ndendic/FastState/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/ndendic/FastState/discussions)** - Community help and ideas
- **[FastHTML Documentation](https://docs.fastht.ml/)** - Core framework docs
- **[Datastar Documentation](https://data-star.dev/)** - Client-side reactivity

---

## 📄 License

FastState is open source software. See the LICENSE file for details.

---

*This documentation covers FastState version 1.0+. For older versions, see the legacy documentation.*