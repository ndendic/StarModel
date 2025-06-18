# StarModel Development Plan
## Entity-Centric Framework with Hybrid Persistence

---

## 🎯 **Core Architecture Decision**

**Keep the `@event` pattern** - it's superior to command classes and perfectly implements clean architecture:

```python
class Product(Entity):  # Renamed from State
    name: str
    stock: int
    
    @event  # This IS the command pattern, just more elegant
    def adjust_stock(self, delta: int):
        self.stock += delta
        # @event handles: command execution, UoW, domain events, persistence
```

**Key Insight**: Our current `@event` decorator already implements the APPLICATION SERVICE LAYER from clean architecture (command dispatcher + UoW + domain events).

---

## 🏗️ **Architecture Alignment**

### Current Implementation ✅ Clean Architecture ✅
```
┌─────────────── PRESENTATION ────────────────┐
│ FastHTML routes → @event methods            │  ✓ Our current web integration
└─────────────────────┬───────────────────────┘
                      │
   🔄 Datastar/SSE    │                           ✓ Our current SSE implementation  
                      ▼
┌─────────────────────────────────────────────┐
│         APPLICATION SERVICE LAYER           │
│  @event decorator = dispatcher + UoW        │  ✓ Our event decorator does this
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│            DOMAIN (Entities)                │
│  Entity methods = Commands (behaviors)      │  ✓ Our current entity pattern
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│       INFRASTRUCTURE ADAPTERS               │
│  StateStore + FastSQLModel integration      │  ✓ Our enhanced persistence
└─────────────────────────────────────────────┘
```

---

## 📋 **Development Phases**

### **Phase 0: Project Organization & Module Structure (✅ COMPLETED)**
*Goal: Reorganize codebase to match clean architecture patterns from ShortManifesto*

#### **✅ Week 1: Module Restructuring (COMPLETED)**

**✅ Step 0.1: Create Proper Module Structure (COMPLETED)**
```
src/starmodel/
├── __init__.py          # Main exports (State, event, StateStore) ✅
├── core/                # Domain layer - framework-agnostic ✅
│   ├── __init__.py      # ✅
│   ├── entity.py        # Base State class (moved from state.py) ✅
│   ├── events.py        # @event decorator (moved from event.py) ✅
│   └── signals.py       # Signal system (moved from signals.py) ✅
├── persistence/         # Infrastructure adapters ✅
│   ├── __init__.py      # ✅
│   ├── base.py          # Abstract interfaces (split from persistence.py) ✅
│   └── memory.py        # MemoryStatePersistence (split from persistence.py) ✅
├── web/                 # Presentation layer (placeholder) ✅
│   └── __init__.py      # ✅
├── ui/                  # UI generation (placeholder) ✅
│   └── __init__.py      # ✅
└── cli/                 # Developer tools (placeholder) ✅
    └── __init__.py      # ✅
```

**✅ Step 0.2: Move Current Code to Proper Modules (COMPLETED)**
```python
# ✅ Moved src/starmodel/state.py → src/starmodel/core/entity.py
# ✅ Moved src/starmodel/event.py → src/starmodel/core/events.py 
# ✅ Moved src/starmodel/signals.py → src/starmodel/core/signals.py
# ✅ Split src/starmodel/persistence.py → src/starmodel/persistence/base.py + memory.py

# ✅ Updated imports in __init__.py to maintain backward compatibility
from starmodel.core.entity import State  # Keep State name for now
from starmodel.core.events import event
from starmodel.persistence.memory import MemoryRepo
```

#### **✅ Week 2: Clean Architecture Validation (COMPLETED)**

**✅ Step 0.3: Validate Layer Separation (COMPLETED)**
```python
# ✅ Ensured clean dependencies:
# core/ → depends on nothing (pure domain logic) ✅
# persistence/ → depends on core/ only ✅
# web/ → depends on core/ and persistence/ ✅
# ui/ → depends on core/ only ✅
# cli/ → depends on all layers for tooling ✅
```

**✅ Step 0.4: Update Demo Application Structure (COMPLETED)**
```python
# ✅ Reorganized app/ to match new architecture:
app/
├── entities/           # Domain entities (NEW) ✅
│   ├── __init__.py     # ✅
│   ├── landing.py      # LandingState (extracted from pages/index.py) ✅
│   ├── counter.py      # CounterState (extracted from pages/counter.py) ✅
│   └── dashboard.py    # DashboardState (extracted from pages/dashboard.py) ✅
├── pages/              # Web presentation layer (updated imports) ✅
│   ├── index.py        # Now imports from entities ✅
│   ├── counter.py      # Now imports from entities ✅
│   └── dashboard.py    # Now imports from entities ✅
└── main.py             # FastHTML app setup (unchanged) ✅
```

**✅ Step 0.5: Manual Testing & Validation**
```bash
# ✅ All imports working correctly:
from starmodel import State, event, StateStore  # ✅ Backward compatibility maintained
from entities import LandingState, CounterState, DashboardState  # ✅ New structure working

# ✅ No functional changes - everything preserved
# ✅ Clean module separation validated
# ✅ Zero breaking changes confirmed
```

### **Phase 1a: Application Service Layer (2-3 weeks)** ⚠️ **CRITICAL PRIORITY**
*Goal: Implement clean architecture patterns from ShortManifesto before adding new features*

#### **Week 3: Application Service Layer Foundation**

**Step 1a.1: Create Application Service Layer**
```python
# Create missing app/ layer to implement APPLICATION SERVICE LAYER
src/starmodel/
├── app/                    # APPLICATION SERVICE LAYER (new)
│   ├── __init__.py
│   ├── dispatcher.py       # Request → Event binding & command execution
│   ├── uow.py             # Unit-of-Work pattern for transactions
│   └── bus.py             # EventBus for SSE/WebSocket coordination
├── adapters/              # INFRASTRUCTURE ADAPTERS
│   ├── __init__.py
│   ├── web_fasthtml.py    # FastHTML router adapter (new)
│   └── persistence/       # Repository adapters (existing)
```

**✅ Step 1a.2: Implement Dispatcher Pattern**
```python
# src/starmodel/app/dispatcher.py
def call_event(state_cls, event_name, request) -> tuple[Any, dict]:
    """Core command execution - replaces direct @event route handling"""
    info = state_cls.events[event_name]
    state = state_cls.get(request)
    bound = info.signature.bind_partial(state, **request.query_params)
    new_state = info.fn(*bound.args, **bound.kwargs)
    cmd_record = {
        "entity": f"{state_cls.__name__}:{state.id}",
        "event": event_name,
        "args": bound.arguments | {"id": state.id},
        "actor": request.user.id if hasattr(request, "user") else None,
        "ts": datetime.utcnow().isoformat(),
    }
    return new_state, cmd_record
```

**✅ Step 1a.3: Implement Unit-of-Work Pattern**
```python
# src/starmodel/app/uow.py
class UnitOfWork:
    """Manages transactions and domain events"""
    def __init__(self, repo_manager, bus):
        self.repo_manager = repo_manager
        self.bus = bus
        self._events = []

    async def commit(self, state, cmd_record):
        # Save state to appropriate repository
        repo = self.repo_manager.for_class(state.__class__)
        await repo.save(state)
        
        # Collect and publish domain events
        self._events.append(cmd_record)
        for event in self._events:
            await self.bus.publish(event)
        self._events.clear()
```

#### **✅ Week 4: Refactor Existing Code to Use App Layer**

**Step 1a.4: Extract Route Registration from @event**
```python
# BEFORE: @event decorator registers routes directly
# AFTER: @event only stores metadata, dispatcher handles execution

# src/starmodel/core/events.py - SIMPLIFIED
def event(fn=None, *, method="GET", selector=None):
    """Store event metadata only - no route registration"""
    def decorator(func):
        func._event_info = EventInfo(
            name=func.__name__,
            method=method,
            selector=selector,
            signature=inspect.signature(func)
        )
        return func
    return decorator(fn) if fn else decorator
```

**✅ Step 1a.5: Implement Repository Pattern**
```python
# src/starmodel/adapters/persistence/__init__.py
class PersistenceManager:
    """Routes entities to appropriate repositories based on model_config"""
    def __init__(self):
        self._backends = {
            EntityStore.SERVER_MEMORY: MemoryRepository(),
            # EntityStore.SERVER_SQL: SQLRepository(),  # Phase 1b
            # EntityStore.SERVER_REDIS: RedisRepository(),  # Phase 2
        }
    
    def for_class(self, entity_class):
        store = entity_class.model_config.get('store', EntityStore.SERVER_MEMORY)
        return self._backends[store]
```

**✅ Step 1a.6: Create FastHTML Adapter**
```python
# src/starmodel/adapters/web_fasthtml.py
def include_entity(app, entity_class, dispatcher, uow):
    """Register entity events as FastHTML routes via dispatcher"""
    for name, info in entity_class.events.items():
        path = f"/{entity_class.__name__.lower()}/{name}"
        
        async def handler(request, _event_name=name):
            new_state, cmd = dispatcher.call_event(entity_class, _event_name, request)
            await uow.commit(new_state, cmd)
            return cmd_to_response(cmd, new_state)
        
        app.add_api_route(path, handler, methods=[info.method])
```

### **Phase 1b: Entity Renaming & FastSQLModel Integration (2 weeks)**
*Goal: Add FastSQLModel support to the clean architecture foundation*

#### **Week 5: State → Entity Renaming**

**✅ Step 1b.1: Rename State → Entity (Zero Functional Changes)**
```python
# src/starmodel/core/entity.py: class State → class Entity
class Entity(BaseModel, metaclass=SignalModelMeta):
    # All existing State functionality preserved
    pass

# Backward compatibility
State = Entity  # Deprecated alias
```

#### **Week 6: FastSQLModel Integration**

**Step 1b.2: Add SQL Repository**
```python
# src/starmodel/adapters/persistence/sql.py
class SQLRepository(RepositoryInterface):
    """FastSQLModel integration via clean repository pattern"""
    
    async def save(self, entity):
        if hasattr(entity, 'save'):
            await entity.save()
    
    async def get(self, entity_class, entity_id):
        if hasattr(entity_class, 'get'):
            return await entity_class.get(entity_id)

# Example SQL-backed entity
class Product(Entity, BaseTable, table=True):
    name: str
    price: float
    
    model_config = {"store": EntityStore.SERVER_SQL}
    
    @event
    def apply_discount(self, percent: float):
        self.price *= (1 - percent / 100)
```

**Step 1b.3: Enhanced EntityStore**
```python
class EntityStore(StrEnum):
    # Existing (keep unchanged)
    SERVER_MEMORY = "server_memory"
    CLIENT_SESSION = "client_session"  
    CLIENT_LOCAL = "client_local"
    
    # New additions
    SERVER_SQL = "server_sql"          # FastSQLModel integration
    SERVER_REDIS = "server_redis"      # Redis backend (Phase 2)
    CUSTOM = "custom"                  # Plugin system (Phase 3)
```

### **Phase 2: Enhanced Persistence & CLI (2-3 weeks)**
*Goal: Production-ready persistence options and improved developer experience*

#### **Week 7-8: Redis & Advanced Persistence**

**Step 2.1: Redis Backend Implementation**
```python
class RedisStatePersistence(StatePersistenceBackend):
    # Implement using existing interface
    # JSON encoding, key prefixes, TTL support
```

**Step 2.2: FastSQLModel Deep Integration**
```python
# Enhanced entity detection
class EntityMeta(SignalModelMeta, ModelMetaclass):
    def __new__(cls, name, bases, namespace, **kwargs):
        # Auto-detect if entity should use SQL persistence
        if BaseTable in bases:
            namespace.setdefault('model_config', {})['store'] = StateStore.SERVER_SQL
```

#### **Week 9: CLI Enhancements**

**Step 2.3: Enhanced CLI Commands**
```bash
# Existing (keep)
starmodel init myapp
starmodel run

# New additions
starmodel migrate        # Alembic for SQL entities
starmodel db shell       # Open database shell
starmodel db reset       # Reset database
starmodel entities list  # Show all entities and their persistence
```

**Step 2.4: Intelligent Project Scaffolding**
```python
# starmodel init creates examples of all entity types:
# - Memory entities (session state)
# - SQL entities (domain models) 
# - Redis entities (cache)
# - Client entities (UI state)
```

### **Phase 3: Plugin Architecture & Admin UI (3-4 weeks)**
*Goal: Extensible framework with visual management interface*

#### **Week 10-12: Plugin System**

**Step 3.1: Plugin Registration System**
```python
# Entry points for plugins
[project.entry-points."starmodel.persistence"]
mongodb = "starmodel_mongo:MongoAdapter"

[project.entry-points."starmodel.cli"] 
backup = "starmodel_backup:BackupCommand"
```

**Step 3.2: Auth Plugin Foundation**
```python
# Basic auth plugin using FastAPI-Users
class User(Entity, BaseTable, table=True):
    email: str
    hashed_password: str
    
    @event
    def login(self, password: str):
        # Handle authentication
```

#### **Week 13: Admin UI**

**Step 3.3: Entity Management Interface**
```python
# Auto-generated admin interface
# - List all entities by type
# - CRUD operations for SQL entities
# - Monitoring for Redis entities  
# - Configuration for all entities
```

### **Phase 4: Production Features (2-3 weeks)**
*Goal: Enterprise-ready features and scaling capabilities*

#### **Week 14-16: Background Tasks & Scaling**

**Step 4.1: Background Task Integration**
```python
@event(background=True)  # Queue for background processing
def send_email(self, to: str, subject: str):
    # Long-running task
```

**Step 4.2: Multi-Instance SSE**
```python
# Redis pub/sub for SSE coordination across instances
# Ensure real-time updates work in distributed setup
```

**Step 4.3: Performance & Monitoring**
```python
# Health checks, metrics, caching strategies
# Connection pooling for SQL entities
```

---

## 🎯 **Key Deliverables by Phase**

### **Phase 0 Exit Criteria: ✅ COMPLETED**
- [x] Clean module structure implemented (`core/`, `persistence/`, `web/`, `ui/`, `cli/`)
- [x] All imports working through organized modules
- [x] Demo app restructured with entities/ and pages/ separation
- [x] No functional changes - everything works exactly as before
- [x] All validation tests passing
- [x] Backward compatibility maintained (`from starmodel import State, event, StateStore`)
- [x] Domain/presentation separation achieved (entities/ vs pages/)
- [x] Layer dependencies validated (core → no deps, persistence → core only)

---

## 🧪 **MANUAL TESTING & APPROVAL REQUIRED**

**Before proceeding to Phase 1, please perform the following manual tests:**

### **Test 1: Basic Import Validation**
```bash
# Test 1: Verify backward compatibility
uv run python -c "import sys; sys.path.insert(0, 'src'); from starmodel import State, event, StateStore; print('✅ Basic imports work')"

# Test 2: Verify new entity structure  
uv run python -c "import sys; sys.path.insert(0, '.'); from app.entities import LandingState, CounterState, DashboardState; print('✅ Entity imports work')"
```

### **Test 2: Demo Application Functionality**
```bash
# Test 3: Run the demo application and verify:
# - Landing page loads without errors
# - Counter functionality works 
# - Dashboard functionality works
# - Real-time updates function properly
# - No console errors in browser

cd app && uv run python main.py
# Open http://localhost:8000 and test all pages
```

### **Test 3: Architecture Validation**
```bash
# Test 4: Verify clean architecture principles
# Check that:
# - core/ modules have no external framework dependencies
# - persistence/ modules only depend on core/
# - entities/ contain business logic only
# - pages/ contain presentation logic only
```

### **✅ APPROVAL CHECKPOINT**
**Once manual testing is complete and all functionality verified, check this box to proceed:**

- [ ] **APPROVED TO PROCEED TO PHASE 1a** 
  - All manual tests passed
  - No functionality regressions found
  - Architecture separation validated
  - Ready for application service layer implementation

---

### **Phase 1a Exit Criteria: Application Service Layer**
- [ ] Application service layer implemented (`app/dispatcher.py`, `app/uow.py`, `app/bus.py`)
- [ ] Route registration moved from `@event` decorator to dispatcher pattern
- [ ] Repository pattern implemented in persistence layer
- [ ] FastHTML adapter created for clean web integration
- [ ] All existing functionality preserved through refactoring
- [ ] Clean architecture validated (app layer between core and adapters)
- [ ] Command execution pattern working with synthetic command records

### **Phase 1b Exit Criteria: Entity Renaming & FastSQLModel**
- [ ] `State` successfully renamed to `Entity` (with backward compatibility)
- [ ] FastSQLModel integration working via repository pattern
- [ ] Demo app shows hybrid persistence (memory + SQL)
- [ ] All tests passing with new architecture

### **Phase 2 Exit Criteria:**
- [ ] Redis backend operational
- [ ] CLI commands for database management
- [ ] Project scaffolding includes all entity types
- [ ] Production deployment guide

### **Phase 3 Exit Criteria:**
- [ ] Plugin system functional with 2+ example plugins
- [ ] Basic admin UI for entity management
- [ ] Auth plugin available

### **Phase 4 Exit Criteria:**
- [ ] Background task system operational
- [ ] Multi-instance deployment working
- [ ] Performance benchmarks met
- [ ] Production monitoring in place

---

## 🔧 **Technical Implementation Notes**

### **FastSQLModel Integration Strategy:**
```python
# Use FastSQLModel's BaseTable as mixin
class BlogPost(Entity, BaseTable, table=True):
    title: str
    content: str
    
    # Entity provides: @event, signals, SSE
    # BaseTable provides: SQL persistence, migrations
    # Perfect harmony!
```

### **Persistence Routing Logic:**
```python
def get_persistence_backend(entity_class):
    store = entity_class.model_config.get('store', StateStore.SERVER_MEMORY)
    
    if store == StateStore.SERVER_SQL:
        return SQLModelPersistence(entity_class)
    elif store == StateStore.SERVER_REDIS:  
        return RedisStatePersistence()
    elif store == StateStore.SERVER_MEMORY:
        return MemoryStatePersistence()
    # etc.
```

### **Migration Strategy:**
1. **Phase 0**: Reorganize modules without functional changes
2. **Week 3**: Feature flag to enable Entity alongside State
3. **Week 4**: Migrate demo app to Entity, keep State working
4. **Week 5**: Deprecation warnings for State usage
5. **Week 6**: Full migration guide and tooling

---

## 📊 **Success Metrics**

| Metric | Phase 1a | Phase 1b | Phase 2 | Phase 3 | Phase 4 |
|--------|----------|----------|---------|---------|---------|
| Boot-to-CRUD time | ≤ 5 min | ≤ 5 min | ≤ 3 min | ≤ 2 min | ≤ 2 min |
| Lines for Todo app | < 50 | < 50 | < 40 | < 30 | < 30 |
| Architecture layers | 4 | 4 | 4 | 4+ | 4+ |
| Entity types supported | 1 | 2 | 4 | 4+ | 4+ |
| Test coverage | > 80% | > 80% | > 85% | > 90% | > 90% |

---

## 🚀 **Why This Revised Plan Works**

1. **Architecture First**: Implement clean architecture foundation before adding features
2. **Aligns with Vision**: Follows ShortManifesto and app-layer.md specifications exactly
3. **Preserves Investment**: Refactor existing code into proper patterns without losing functionality
4. **Validates @event Pattern**: Proves @event + dispatcher is superior to command classes
5. **Enables Future Growth**: Clean architecture makes FastSQLModel, Redis, and plugins easy to add
6. **Production Ready**: Proper separation of concerns from the start

## 🎯 **Critical Success Factors**

1. **Phase 1a MUST complete before Phase 1b**: Can't add FastSQLModel to architecture that needs refactoring
2. **Repository Pattern is Key**: Enables clean persistence abstraction for all storage backends
3. **Dispatcher Pattern is Essential**: Separates command execution from HTTP routing
4. **Unit-of-Work Enables Transactions**: Critical for SQL and Redis backends
5. **EventBus Enables Scaling**: Foundation for multi-instance and WebSocket support

**Next Step**: Begin Phase 1a, Week 3 - Create application service layer foundation as specified in app-layer.md