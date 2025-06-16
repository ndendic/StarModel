# Design Document: Entity-Centric Python Web Framework (FastHTML + MonsterUI + FastSQLModel + Datastar)

## Introduction

This document presents the **architecture and philosophy** for StarModel, a Python-based, entity-centric web framework designed for **rapid prototyping** without sacrificing **production readiness**. StarModel combines a **batteries-included** approach with modular flexibility. By default, it leverages **FastHTML** (server-side HTML generation), **MonsterUI** (Tailwind CSS components), **FastSQLModel** (for SQL persistence), hybrid persistence strategies, and **Datastar** (Server-Sent Events for real-time interactivity). 

The goal is to let developers focus on defining their core **business entities** (data models and logic) using the elegant `@event` pattern, and have the system automatically generate appropriate persistence, UI, and backend infrastructure around those definitions.

## Philosophy & Key Principles

**1. Define Entities with Behavior, Get Everything Else for Free.** The core philosophy is that developers should primarily define _what_ their application is about – **entities with behavior** – using natural Python methods decorated with `@event`. The framework automatically generates UI, routes, persistence, and real-time updates. Whether you need memory-based session state, SQL-backed domain models, or Redis-cached data, you simply declare your entity and choose the appropriate persistence strategy.

**2. @event Pattern Over Command Classes.** We use method-based commands (`@event` decorator) rather than separate command classes. This is more Pythonic, reduces boilerplate, keeps behavior with data, and provides better IDE support. The `@event` decorator handles command execution, unit-of-work patterns, domain events, and SSE responses automatically.

**3. Fast Prototyping _and_ Scalable Production.** The system is built to be useful in the first hour of development and the first year of deployment alike. Start with SQLite and memory persistence for instant prototyping, then seamlessly upgrade to Postgres and Redis for production. The same entity definitions work across all environments.

**4. Opinionated Defaults, Pluggable Flexibility.** The framework comes with **intelligent defaults** that adapt to your entity configuration – SQL entities get database persistence with migrations, memory entities get fast in-process storage, Redis entities get TTL management. However, **every layer is replaceable** via adapters: swap MonsterUI for custom components, add custom persistence backends, or expose REST APIs alongside HTML pages.

**5. Clean Architecture with Hexagonal Design.** The framework implements clean architecture principles with entities at the core, surrounded by application services (the `@event` decorator), and infrastructure adapters (persistence, UI, SSE). This ensures business logic remains isolated from technology choices while enabling easy testing and extension.

## Core Design Concepts and Patterns

The framework employs established design patterns in a Pythonic way. The architecture follows a **layered system** with **Entities at the core** and various **adapters** around them.

### **Entities (Domain Model with Behavior)**

Entities are Python classes that represent business concepts, encapsulating both **attributes** (data fields) and **behavior** (methods decorated with `@event`). The framework supports different persistence strategies based on entity configuration:

```python
# Memory-based entity (session state, caching)
class UserSession(Entity):
    cart_items: list = []
    preferences: dict = {}
    
    model_config = {"store": StateStore.SERVER_MEMORY}
    
    @event
    def add_to_cart(self, item_id: str, quantity: int):
        self.cart_items.append({"id": item_id, "qty": quantity})

# SQL-backed entity (persistent domain models)  
from fastsqlmodel import BaseTable

class Product(Entity, BaseTable, table=True):
    name: str
    price: float
    stock: int
    
    model_config = {"store": StateStore.SERVER_SQL}
    
    @event
    def adjust_stock(self, delta: int):
        if self.stock + delta < 0:
            raise ValueError("Insufficient stock")
        self.stock += delta

# Redis-cached entity (fast lookup, TTL)
class UserAnalytics(Entity):
    user_id: str
    page_views: int = 0
    last_activity: datetime
    
    model_config = {"store": StateStore.SERVER_REDIS, "ttl": 3600}
    
    @event
    def track_page_view(self, page: str):
        self.page_views += 1
        self.last_activity = datetime.now()
```

### **The @event Pattern (Application Service Layer)**

The `@event` decorator works with the application service layer to provide clean command execution. The decorator stores metadata while the dispatcher handles execution:

- **Command Metadata**: `@event` decorator stores method signatures and configuration
- **Command Dispatch**: Application dispatcher routes web requests to entity methods
- **Unit of Work**: Manages transactions, persistence, and domain events
- **Domain Events**: EventBus triggers SSE updates to connected clients  
- **Parameter Injection**: Dispatcher extracts parameters from HTTP requests and Datastar payloads
- **Response Generation**: Returns appropriate HTML fragments or SSE streams via adapters

```python
@event  # Default: GET request, automatic SSE response
def increment_counter(self):
    self.count += 1

@event(method="post", selector="#status")  # Custom HTTP method and DOM target
def reset_counter(self):
    self.count = 0
    return Div("Counter reset!", id="status")

@event  # Async support for long-running operations
async def process_batch(self, items: list):
    for i, item in enumerate(items):
        await self.process_item(item)
        yield Div(f"Processed {i+1}/{len(items)}", id="progress")
```

### **Hybrid Persistence Architecture**

The framework provides a unified persistence interface that adapts to different storage backends:

```python
class StateStore(StrEnum):
    SERVER_MEMORY = "server_memory"    # In-process, fast, session-scoped
    SERVER_SQL = "server_sql"          # FastSQLModel integration  
    SERVER_REDIS = "server_redis"      # Distributed cache with TTL
    CLIENT_SESSION = "client_session"  # Browser sessionStorage via Datastar
    CLIENT_LOCAL = "client_local"      # Browser localStorage via Datastar
    CUSTOM = "custom"                  # Plugin-provided backends
```

Each entity declares its preferred persistence strategy, and the framework handles the implementation details automatically.

### **Adapters (Ports and Adapters Architecture)**

The system communicates with the outside world through interchangeable adapters:

- **UI Adapter**: FastHTML + MonsterUI generates forms, lists, and detail pages automatically based on entity schemas. Components are styled with Tailwind CSS and include real-time binding via Datastar.

- **Persistence Adapter**: Multi-modal persistence system that routes to appropriate backends (FastSQLModel for SQL, Redis for caching, memory for sessions). Each adapter implements the same interface but optimizes for its storage characteristics.

- **Real-Time Events Adapter**: Datastar integration for Server-Sent Events. Entity changes automatically broadcast to connected clients with appropriate targeting (SQL entity changes go to all viewers, session entity changes go to the owning client).

- **Web Adapter**: FastHTML integration that auto-generates RESTful routes based on entity definitions and `@event` methods. Handles request parsing, parameter injection, and response formatting.

## Module Structure and Components

The framework follows **clean architecture principles** with clear layer separation:

### **Core Domain Layer**
- **`starmodel.core`** – Base Entity class, @event decorator, signal system, and entity registration. Framework-agnostic domain logic.

### **Application Service Layer**  
- **`starmodel.app`** – Application services implementing clean architecture patterns:
  - **`dispatcher.py`** – Request → Event binding and command execution
  - **`uow.py`** – Unit-of-Work pattern for transactions and domain events
  - **`bus.py`** – EventBus interface for SSE, WebSocket, and multi-instance coordination

### **Infrastructure Adapters**
- **`starmodel.adapters`** – Infrastructure adapters implementing ports and adapters pattern:
  - **`persistence/`** – Multi-modal persistence adapters (memory, Redis, FastSQLModel, client-side)
  - **`web_fasthtml.py`** – FastHTML integration and auto-route generation  
  - **`ui_monster.py`** – MonsterUI integration and automatic UI generation
  - **`sse_datastar.py`** – Datastar integration for real-time updates

### **Developer Tools**
- **`starmodel.cli`** – Developer tools: project scaffolding, development server, database migrations, entity management utilities.

- **`starmodel.plugins`** – Plugin architecture for extending persistence backends, UI components, CLI commands, and admin features.

## Developer Workflow and CLI

The `starmodel` CLI provides a smooth developer experience:

```bash
# Create new project with example entities
starmodel init myapp

# Run development server with auto-reload  
starmodel run

# Database operations (for SQL entities)
starmodel migrate
starmodel db shell
starmodel db reset

# Entity management
starmodel entities list
starmodel entities inspect Product
```

The CLI automatically detects entity types and sets up appropriate infrastructure. For example, if your project has SQL entities, it configures database connections and migration support. If you have Redis entities, it checks Redis availability and provides cache management tools.

## Entity Definition and Automatic Infrastructure Generation

The framework's power comes from automatic infrastructure generation based on entity definitions:

### **SQL-Backed Entities with FastSQLModel**

```python
from fastsqlmodel import BaseTable

class BlogPost(Entity, BaseTable, table=True):
    title: str
    content: str
    published: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    
    @event
    def publish(self):
        self.published = True
        
    @event  
    def update_content(self, new_content: str):
        self.content = new_content
```

**Automatic Generation:**
- Database table with proper schema
- Alembic migrations when schema changes
- CRUD routes: `GET /blogposts`, `POST /blogposts`, `GET /blogposts/{id}`, etc.
- Admin interface with list/form views
- Real-time updates when posts are published

### **Memory-Based Entities for Session State**

```python
class ShoppingCart(Entity):
    items: list[dict] = []
    total: float = 0.0
    
    model_config = {"store": StateStore.SERVER_MEMORY}
    
    @event
    def add_item(self, product_id: str, quantity: int, price: float):
        self.items.append({"id": product_id, "qty": quantity, "price": price})
        self.total += quantity * price
```

**Automatic Generation:**
- Session-scoped storage (per-user isolation)
- Fast in-memory operations
- Real-time UI updates via SSE
- No database overhead

### **Redis-Cached Entities for Performance**

```python
class RecentActivity(Entity):
    user_id: str
    actions: list[str] = []
    
    model_config = {"store": StateStore.SERVER_REDIS, "ttl": 1800}
    
    @event
    def log_action(self, action: str):
        self.actions.append(f"{datetime.now()}: {action}")
        if len(self.actions) > 100:
            self.actions = self.actions[-100:]  # Keep last 100
```

**Automatic Generation:**
- Redis storage with TTL
- Cross-instance sharing
- Automatic cleanup
- High-performance access

## Real-Time Interactivity with Datastar

The framework uses Datastar for server-driven real-time updates without requiring JavaScript:

**Entity-Aware SSE Patterns:**
- SQL entity changes broadcast to all connected clients viewing that entity
- Memory entity changes update the owning session
- Redis entity changes can trigger dashboard updates
- Client entity changes sync between browser tabs

**Developer Experience:**
```python
@event
async def long_running_task(self):
    for i in range(10):
        await asyncio.sleep(1)
        self.progress = (i + 1) * 10
        yield Div(f"Progress: {self.progress}%", id="progress-bar")
```

The framework automatically handles SSE streaming, client targeting, and DOM updates.

## Extensibility and Plugin Architecture

The framework is designed for extensibility:

**Persistence Plugins:**
```python
# Custom persistence backend
class MongoStatePersistence(StatePersistenceBackend):
    async def save_state(self, entity):
        # Custom implementation
```

**CLI Plugins:**
```python
# Add custom CLI commands
@click.command()
def backup():
    """Backup all entities"""
    # Implementation
```

**UI Plugins:**
```python
# Custom UI components
class RichTextEditor(Component):
    """Rich text editor for content fields"""
```

## Roadmap and Development Phases

### **Phase 1a: Application Service Layer (2-3 weeks)** ⚠️ **CRITICAL PRIORITY**
- Implement clean architecture foundation (`app/dispatcher.py`, `app/uow.py`, `app/bus.py`)
- Extract route registration from `@event` decorator to dispatcher pattern
- Implement repository pattern in persistence layer
- Create FastHTML adapter for clean web integration
- Validate clean architecture separation

### **Phase 1b: Entity Renaming & FastSQLModel (2 weeks)**
- Rename State → Entity with backward compatibility
- Integrate FastSQLModel via repository pattern
- Enhanced EntityStore with SQL/Redis options
- Update demo application with hybrid persistence

### **Phase 2: Enhanced Persistence & CLI (2-3 weeks)**
- Redis backend implementation via repository pattern
- Database management CLI commands  
- Intelligent project scaffolding
- Production deployment guides

### **Phase 3: Plugin Architecture (3-4 weeks)**
- Plugin system with entry points
- Basic auth plugin
- Admin UI for entity management
- Extension documentation

### **Phase 4: Production Features (2-3 weeks)**
- Background task support via EventBus
- Multi-instance SSE coordination
- Performance monitoring
- Enterprise deployment guides

## Conclusion

StarModel represents a new approach to Python web development that **prioritizes developer productivity without sacrificing architectural clarity**. By combining the elegant `@event` pattern with hybrid persistence strategies and automatic infrastructure generation, developers can focus on business logic while the framework handles the technical complexity.

The integration with FastSQLModel provides robust SQL persistence, while the multi-modal approach supports everything from session state to high-performance caching. The clean architecture ensures that applications built with StarModel can grow from prototypes to production systems without requiring rewrites.

**Entity-first, @event-driven, persistently flexible.**