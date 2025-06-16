# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run the application**: `python app/main.py` or `python -m app.main`
- **Install dependencies**: `uv sync` (uses uv for dependency management)
- **Add dependencies**: `uv add <package-name>`
- **Install dev dependencies**: `uv sync --group dev`
- **Run tests**: No unified test runner configured (tests are not currently present in the project)

## Project Architecture

StarModel is an **entity-centric Python web framework** that follows the philosophy: **"Write an Entity once → get database, API, and live UI for free."** The framework merges instant-CRUD capabilities with real-time interactivity, all in **pure Python** without frontend build tooling.

### **Core Philosophy**
1. **Entity First** – Data **and** behavior live together in a single class; developers declare `@event` methods, not controllers
2. **Opinionated On-Ramp, Pluggable Runway** – FastHTML + MonsterUI + SQLite get you an MVP in minutes; every layer can be swapped via adapters
3. **Progressive Disclosure** – Hello-world in < 30 lines; advanced teams can override routing, persistence, UI, or background tasks without rewrites
4. **Clean Architecture Core** – Domain logic is isolated from web, DB, or JS; ports-and-adapters keep tech choices swappable
5. **Hybrid Persistence** – Each Entity chooses its own store: in-memory, Redis, SQL, browser storage, or any custom backend

### **Clean Architecture Layers**

```
┌────────────── PRESENTATION (adapters) ───────────────┐
│ FastHTML routes │ REST / GraphQL (opt) │ CLI │ …     │
└────────────┬────────────┬────────────┬───────────────┘
             │            │            │
  🔄 Datastar / SSE / WS  │            │
             ▼            ▼            ▼
┌──────────────────────────────────────────────────────┐
│              APPLICATION SERVICE LAYER               │
│  • Event dispatcher  • Unit‑of‑Work  • EventBus      │
└────────────┬────────────┬────────────┬───────────────┘
             │ emits DomainEvents│            │
             ▼            ▼            ▼
┌──────────────────────────────────────────────────────┐
│                 DOMAIN  (Entities)                   │
│  • Entity (Pydantic/SQLModel)  • @event methods      │
│  • Value objects  • pure domain services             │
└────────────┬────────────┬────────────┬───────────────┘
             │            │            │
             ▼            ▼            ▼
┌─────────────── INFRASTRUCTURE ADAPTERS ──────────────┐
│ MemoryRepo │ RedisRepo │ SQLRepo (FastSQLModel) │ …  │
└──────────────────────────────────────────────────────┘
```

### **Core Components**

1. **Entity Base Class** (`src/starmodel/core/entity.py`): 
   - **Entity-Centric Design**: Data structure and behavior unified in single classes
   - **@event Pattern**: Methods decorated with `@event` become HTTP endpoints automatically
   - **Signal-based Architecture**: Uses `SignalModelMeta` metaclass for automatic `field_signal` descriptors
   - **EntityStore Enumeration**: Configure persistence with `EntityStore` enum (SERVER_MEMORY, SERVER_SQL, SERVER_REDIS, CLIENT_SESSION, CLIENT_LOCAL, CUSTOM)
   - **Hybrid Persistence**: Each entity chooses its own storage backend
   - **Pydantic Foundation**: Built on Pydantic BaseModel for type safety and validation

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

4. **Unified Persistence Layer** (`src/starmodel/persistence/`):
   - **Memory Backend**: `MemoryEntityPersistence` serves as unified cache and persistence
   - **Instance Storage**: Stores whole Entity instances (not serialized data) for efficiency
   - **TTL Support**: Built-in expiration with cleanup via `save(ttl=X)` parameter
   - **Simple API**: Just `save()`, `delete()`, and `exists()` methods

### Key Architectural Features

#### **Entity-Centric Design**:
- All business logic and data structure defined in single `Entity` classes
- FastHTML dependency injection for automatic entity resolution
- Pydantic-based validation and type safety
- Clean separation between entity definition and web routing

#### **Automatic Signal Generation**:
- `SignalModelMeta` metaclass automatically creates `field_signal` descriptors
- Generated signals work seamlessly with Datastar's reactive system
- Optional namespacing for complex applications

#### **Event System**:
- `@event` decorator converts methods to HTTP endpoints automatically
- URL generation methods for Datastar attributes
- SSE streaming for real-time updates

### **Default Technology Stack**

| Layer       | Default Choice                          | How to Swap                                  |
| ----------- | --------------------------------------- | -------------------------------------------- |
| Web Engine  | **FastHTML** (Starlette core)           | Any ASGI via router adapter                  |
| UI Kit      | **MonsterUI** (Tailwind components)     | Other FastHTML kit or React via REST adapter |
| ORM / Table | **SQLModel + BaseTable** (FastSQLModel) | Tortoise / PonyORM / custom SQLAlchemy       |
| DB Engine   | **SQLite**                              | Postgres, MySQL via URL or alt repo          |
| Cache       | **Server Memory**                       | Redis via `RedisStatePersistence`            |
| Realtime    | **Datastar (SSE)**                      | WebSocket plugin (Phase 4)                   |
| Auth        | **FastHTML‑Auth simple**                | OAuth, AzureAD plugin                        |
| CLI         | `starmodel`: `init`, `run`              | New commands via entry‑point plugins         |

### **Entity Management Flow**

1. **Entity Definition**: Define entities with data fields and `@event` methods for behavior
2. **Persistence Selection**: Each entity chooses its storage backend via `model_config`
3. **Automatic Infrastructure**: Framework generates routes, signals, UI components, and persistence
4. **Real-time Updates**: `@event` methods trigger SSE responses with automatic state synchronization
5. **Progressive Enhancement**: Start with memory/SQLite, scale to Redis/Postgres without code changes

### Current Configuration System

#### **Simple model_config**:
```python
class Counter(Entity):
    # Default config - no setup needed
    count: int = 0
    update_count: int = 0

class AdvancedEntity(Entity):
    data: dict = {}
    
    model_config = {
        "store": EntityStore.CLIENT_SESSION,      # Where to store
        "auto_persist": True,                     # Auto-save changes
        "persistence_backend": memory_persistence, # How to store
        "sync_with_client": True,                # Client sync
        "use_namespace": True,                   # Namespaced signals
    }
```

#### **EntityStore Options**:
- `EntityStore.SERVER_MEMORY` - Server-side memory persistence (default)
- `EntityStore.SERVER_SQL` - FastSQLModel integration (planned Phase 1)
- `EntityStore.SERVER_REDIS` - Redis backend with TTL (planned Phase 2)
- `EntityStore.CLIENT_SESSION` - Browser sessionStorage (Datastar managed)
- `EntityStore.CLIENT_LOCAL` - Browser localStorage (Datastar managed)  
- `EntityStore.CUSTOM` - Custom persistence backend

### Demo Application Structure

The demo showcases StarModel capabilities with clean, modular pages and entities:

- **Home (`/`)**: Landing page with basic entity demonstration
- **Counter (`/counter`)**: Enhanced counter with real-time streaming
- **Dashboard (`/dashboard`)**: Complex entity with computed fields and charts
- **Admin (`/admin`)**: Global settings with system monitoring
- **Auth (`/auth-demo`)**: User profiles with authentication
- **Chat (`/chat`)**: Real-time collaboration demo
- **Product (`/product/{id}`)**: Record-scoped entities tied to IDs

### Application Structure
```
app/
├── entities/          # Entity definitions (business logic)
│   ├── counter.py     # CounterEntity
│   ├── dashboard.py   # DashboardEntity  
│   └── landing.py     # LandingEntity
├── pages/             # FastHTML route handlers
│   ├── components/    # Reusable UI components
│   ├── index.py       # Landing page routes
│   ├── counter.py     # Counter page routes
│   ├── dashboard.py   # Dashboard page routes
│   └── templates.py   # Shared page templates
└── main.py           # Application entry point
```

## Development Patterns

### **Entity Definition Pattern**:
```python
# Define entity with data and behavior together
class Counter(Entity):
    count: int = 0
    update_count: int = 0
    
    @event  # Automatically becomes HTTP endpoint
    def increment(self, amount: int = 1):
        self.count += amount
        self.update_count += 1
    
    @event(method="post", selector="#counter")  # Custom config
    def reset(self):
        self.count = 0
        self.update_count += 1
        return Counter.count_signal  # Return updated signal
```

### **Page Integration Pattern**:
```python
# Import entities and use in FastHTML routes
from app.entities.counter import Counter

@rt('/counter')
def counter_page(req: Request):
    # Entities are automatically resolved by FastHTML DI
    return Main(
        H1("Counter Demo"),
        Button("+1", data_on_click=Counter.increment(1)),  # Generated URL method
        Span(data_text=Counter.count_signal),  # Generated signal
        P(f"Updates: {Counter.update_count_signal}")
    )

# Remember to register entity routes
from starmodel import entities_rt
entities_rt.to_app(app)  # Add entity endpoints to app
```

### **Signal Usage**:
```python
# Generated signals for Datastar binding
Span(data_text=Counter.count_signal)  # → data-text="$count" or "$Counter.count"
Input(data_bind=Counter.text_signal)  # Two-way binding

# Access signals programmatically  
counter.signal('count')  # Returns "$count" or "$Counter.count"
```

## **Current Development Status**

**Phase 0: ✅ COMPLETED** - Project Organization & Module Structure
- [x] Clean module structure implemented (`core/`, `persistence/`, `web/`, `ui/`, `cli/`)
- [x] All imports working through organized modules
- [x] Demo app restructured with entities/ and pages/ separation
- [x] Backward compatibility maintained (`from starmodel import Entity, event, EntityStore`)
- [x] Domain/presentation separation achieved (entities/ vs pages/)

**Phase 1a: 🎯 NEXT PRIORITY** - Application Service Layer (2-3 weeks) ⚠️ **CRITICAL**
- [ ] Create application service layer (`app/dispatcher.py`, `app/uow.py`, `app/bus.py`)
- [ ] Extract route registration from `@event` decorator to dispatcher pattern
- [ ] Implement repository pattern in persistence layer
- [ ] Create FastHTML adapter for clean web integration
- [ ] Validate clean architecture separation (app layer between core and adapters)

**Phase 1b: FOLLOWING** - Entity Renaming & FastSQLModel Integration (2 weeks)
- [ ] State → Entity renaming with backward compatibility
- [ ] FastSQLModel integration via repository pattern
- [ ] Enhanced EntityStore with SQL/Redis options
- [ ] Multi-modal persistence examples in demo app

## **Development Roadmap**

| Phase                           | Deliverables                                                                 | Exit Test                                        |
| ------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------ |
| **P0 Spike** ✅                  | `@event` API + Memory repo + Datastar live counter                           | Two tabs show counter sync                       |
| **P1a Application Service** 🎯   | Dispatcher + UoW + Bus + Repository pattern + FastHTML adapter              | Clean architecture validated, all tests pass    |
| **P1b Entity + FastSQLModel** 🔄 | Entity renaming + FastSQLModel integration via repository pattern           | `starmodel init demo` → CRUD works live          |
| **P2 Pluggable Persistence**   | Redis repo; CLI `migrate`; hybrid storage examples                          | Hybrid Redis+SQL sample passes tests             |
| **P3 Plugin Framework**        | Entry‑point loader; Admin UI alpha; Auth plugin                              | Third‑party plugin adds route w/out core changes |
| **P4 Prod Harden**             | Task queue; WebSocket option; health/metrics                                 | 3‑node docker‑compose sync demo                  |

## **🎯 StarModel Project Memory & Context**

### **Core Mission**
StarModel is an **entity-centric Python web framework** that implements the philosophy: **"Write an Entity once → get database, API, and live UI for free."** We're building a framework that merges instant-CRUD capabilities with real-time interactivity, all in pure Python without frontend build tooling.

### **Key Architectural Decisions**
- **@event Pattern**: Superior to command classes - implements clean architecture's APPLICATION SERVICE LAYER
- **Clean Architecture**: Core → App → Adapters layer separation with Domain logic isolated from infrastructure  
- **Hybrid Persistence**: Each entity chooses its storage backend independently (memory, SQL, Redis, client)
- **Repository Pattern**: Essential for clean persistence abstraction across all storage backends
- **Dispatcher Pattern**: Separates command execution from HTTP routing for better architecture

### **Current Critical Priority: Phase 1a**
- **MUST implement application service layer BEFORE adding FastSQLModel**
- Create `app/dispatcher.py`, `app/uow.py`, `app/bus.py` as specified in app-layer.md
- Extract route registration from `@event` decorator to dispatcher pattern
- Implement repository pattern for clean persistence abstraction
- This foundation enables all future features (FastSQLModel, Redis, plugins)

### **Document Alignment Status**
- ✅ ShortManifesto-3.md: North star vision with clean architecture
- ✅ app-layer.md: Implementation roadmap for Phase 1a (CRITICAL REFERENCE)  
- ✅ DevelopmentPlan.md: Detailed Phase 1a → 1b → 2+ progression
- ✅ Manifest.md: Updated to match clean architecture vision
- ✅ CLAUDE.md: Current status and immediate priorities

### **Success Criteria for Phase 1a**
- Application service layer implemented with clean architecture separation
- Route registration moved from decorator to dispatcher 
- Repository pattern working for persistence abstraction
- All existing functionality preserved through refactoring
- Foundation ready for FastSQLModel integration in Phase 1b

**Repository**: Uses `main` branch as default, currently in `refactoring-phase1` branch for Phase 1 work

## Entity Development API

```python
# Basic entity definition with automatic signal generation
class Counter(Entity):
    count: int = 0
    
    @event
    def increment(self, amount: int = 1):
        self.count += amount

# Generated URL methods for Datastar (automatic)
Button("+1", data_on_click=Counter.increment(1))
Input(data_bind=Counter.count_signal)

# Signal access for reactive binding  
Span(data_text=Counter.count_signal)  # → "$count" or "$Counter.count"
```

## **Multi-Modal Persistence Examples**

```python
# Memory-based entity (session state, caching)
class UserSession(Entity):
    cart_items: list = []
    preferences: dict = {}
    
    model_config = {"store": EntityStore.SERVER_MEMORY}
    
    @event
    def add_to_cart(self, item_id: str, quantity: int):
        self.cart_items.append({"id": item_id, "qty": quantity})

# SQL-backed entity (persistent domain models) - PLANNED PHASE 1
from fastsqlmodel import BaseTable

class Product(Entity, BaseTable, table=True):
    name: str
    price: float
    stock: int
    
    model_config = {"store": EntityStore.SERVER_SQL}
    
    @event
    def adjust_stock(self, delta: int):
        if self.stock + delta < 0:
            raise ValueError("Insufficient stock")
        self.stock += delta

# Redis-cached entity (fast lookup, TTL) - PLANNED PHASE 2
class UserAnalytics(Entity):
    user_id: str
    page_views: int = 0
    last_activity: datetime
    
    model_config = {"store": EntityStore.SERVER_REDIS, "ttl": 3600}
    
    @event
    def track_page_view(self, page: str):
        self.page_views += 1
        self.last_activity = datetime.now()

# Client-side storage entity (pure UI state)
class UIPreferences(Entity):
    theme: str = "light"
    sidebar_collapsed: bool = False
    
    model_config = {"store": EntityStore.CLIENT_LOCAL}
    
    @event
    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
```

## **Vision & Goals**

**Entity-first · decorator-driven · adapter-powered · pure Python**

StarModel marries **rapid prototyping** with **long-term viability**. Define an Entity, decorate behavior with `@event`, and watch your app come alive with live HTML, real-time sync, and swappable persistence.

### **Key Success Metrics**

| Metric | Phase 1 Target | Phase 2 Target | Production Target |
|--------|---------------|---------------|------------------|
| Boot-to-CRUD time | ≤ 5 min | ≤ 3 min | ≤ 2 min |
| Lines for Todo app | < 50 | < 40 | < 30 |
| Entity types supported | 2 | 4 | 4+ |
| Real-time capabilities | SSE | SSE + WebSocket | Multi-instance sync |

### **Framework Capabilities**

1. **"Write Once, Get Everything"**: Define entity → automatic database, API, and live UI
2. **Hybrid Persistence**: Memory, SQL, Redis, client storage - each entity chooses independently
3. **Clean Architecture**: Domain logic isolated from infrastructure concerns
4. **Progressive Enhancement**: Start simple, scale to enterprise without rewrites
5. **Pure Python**: No frontend build step, no JavaScript required
6. **Real-time by Default**: SSE streaming and state synchronization built-in
7. **Pluggable Everything**: Swap any layer via adapters (persistence, UI, auth, etc.)
8. **Production Ready**: Clear path from prototype to multi-instance deployment

**Current Focus**: Phase 1a implementation of application service layer foundation - CRITICAL for all future development.

## **🚀 Immediate Next Actions**

When working on this codebase, the **immediate priority** is Phase 1a implementation:

1. **Reference app-layer.md** for detailed implementation steps
2. **Create application service layer**: `app/dispatcher.py`, `app/uow.py`, `app/bus.py`  
3. **Refactor @event decorator** to store metadata only, move route registration to dispatcher
4. **Implement repository pattern** for persistence abstraction
5. **Validate clean architecture** separation before proceeding to Phase 1b

**Remember**: The application service layer foundation MUST be completed before adding FastSQLModel or other new features. This ensures we build on solid architectural principles rather than technical debt.