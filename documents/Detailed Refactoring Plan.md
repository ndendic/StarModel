# StarModel Detailed Refactoring Plan

## Executive Summary

This document provides a detailed refactoring plan for StarModel to achieve true clean architecture separation, eliminate tight coupling, and enable pluggable component swapping. The refactoring combines **clean architecture principles** with **screaming architecture organization** to create a domain-centric, self-documenting framework structure.

## Refactoring Structure Overview

The refactoring follows an integrated approach combining architectural improvements with organizational restructuring:

```
Phase 0: Screaming Architecture Migration (Foundation)
    ↓
Phase 1: Application Service Layer Foundation  
    ↓
Phase 2: Persistence Abstraction Layer
    ↓
Phase 3: Web Adapter Decoupling
    ↓
Phase 4: SQL Integration Cleanup
```

Each phase builds upon the previous, ensuring we don't break existing functionality while progressively improving both the architecture and code organization.

## Key Integration Points

### **Screaming Architecture + Clean Architecture**
- **Domain Structure**: Organization reflects what StarModel does (entities, events, real-time)
- **Clean Boundaries**: Proper separation between domain, application, and infrastructure layers
- **Self-Documenting**: Directory names immediately communicate purpose and capabilities
- **Plugin-Ready**: Clear extension points for new backends, protocols, and frameworks

---

## Phase 0: Screaming Architecture Migration (Foundation)

### **Objective**
Reorganize the codebase from framework-centric to domain-centric structure, making StarModel's purpose immediately clear from the directory organization.

### **Current Problem**
The existing structure is framework-centric and doesn't communicate what StarModel does:

```
src/starmodel/
├── core/              # Generic "core" - what does this do?
├── persistence/       # Generic "persistence" - for what?
├── web/              # Generic "web" - what kind of web app?
├── adapters/         # Generic "adapters" - adapting what?
└── app/              # Generic "app" - what does it do?
```

### **Target Screaming Architecture**

```
framework/                          # StarModel Framework Core
├── entities/                      # 🎯 THE HEART - Entity-centric design
│   ├── lifecycle/                 # Entity creation, updates, deletion
│   ├── behavior/                  # Entity business logic & @event methods
│   ├── composition/               # Entity relationships & aggregates
│   └── validation/                # Entity validation & constraints
│
├── events/                        # 🚀 EVENT-DRIVEN INTERACTIONS
│   ├── commands/                  # User commands (@event methods)
│   ├── handlers/                  # Event processing logic
│   ├── dispatching/               # Command routing & execution
│   └── streaming/                 # Event streams & propagation
│
├── realtime/                      # ⚡ LIVE INTERACTIONS
│   ├── synchronization/           # State sync across clients
│   ├── broadcasting/              # Multi-user event propagation
│   ├── connections/               # Client connection management
│   └── protocols/                 # SSE, WebSocket, etc.
│
├── reactivity/                    # 🔄 REACTIVE STATE MANAGEMENT
│   ├── signals/                   # Reactive signals system
│   ├── binding/                   # Data-UI binding mechanisms
│   ├── updates/                   # Automatic UI updates
│   └── subscriptions/             # Change subscriptions
│
├── persistence/                   # 💾 DATA STORAGE & RETRIEVAL
│   ├── backends/                  # Storage implementations
│   ├── repositories/              # Data access patterns
│   ├── transactions/              # ACID operations & UoW
│   └── caching/                   # Performance optimizations
│
└── infrastructure/                # 🔧 TECHNICAL IMPLEMENTATION
    ├── web/                       # Web framework adapters
    ├── storage/                   # Database & cache adapters
    ├── messaging/                 # Event bus implementations
    └── deployment/                # Configuration & setup
```

### **Implementation Steps**

#### 0.1 Create New Directory Structure
```bash
# Create framework directory structure
mkdir -p framework/{entities,events,realtime,reactivity,persistence,infrastructure}
mkdir -p framework/entities/{lifecycle,behavior,composition,validation}
mkdir -p framework/events/{commands,handlers,dispatching,streaming}
mkdir -p framework/realtime/{synchronization,broadcasting,connections,protocols}
mkdir -p framework/reactivity/{signals,binding,updates,subscriptions}
mkdir -p framework/persistence/{backends,repositories,transactions,caching}
mkdir -p framework/infrastructure/{web,storage,messaging,deployment}

# Create examples directory structure
mkdir -p examples/{counter-app,dashboard-app,full-demo}
mkdir -p examples/counter-app/{entities,pages}
mkdir -p examples/dashboard-app/{entities,pages}
mkdir -p examples/full-demo/{entities,pages}
```

#### 0.2 Establish Migration Mapping
```python
# File migration mapping for Phase 0
MIGRATION_MAPPING = {
    # Core entity system
    "src/starmodel/core/entity.py": "framework/entities/lifecycle/entity.py",
    "src/starmodel/core/events.py": "framework/events/commands/event.py",
    "src/starmodel/core/signals.py": "framework/reactivity/signals/signal_system.py",
    
    # Application layer
    "src/starmodel/app/dispatcher.py": "framework/events/dispatching/dispatcher.py",
    "src/starmodel/app/bus.py": "framework/events/streaming/event_bus.py",
    "src/starmodel/app/uow.py": "framework/persistence/transactions/unit_of_work.py",
    
    # Persistence layer
    "src/starmodel/persistence/memory.py": "framework/persistence/backends/memory.py",
    "src/starmodel/persistence/sql.py": "framework/persistence/backends/sql.py",
    "src/starmodel/persistence/base.py": "framework/persistence/repositories/base.py",
    
    # Infrastructure
    "src/starmodel/adapters/fasthtml.py": "framework/infrastructure/web/fasthtml_adapter.py",
    "src/starmodel/web/": "framework/infrastructure/web/",
    
    # Demo applications
    "app/entities/": "examples/full-demo/entities/",
    "app/pages/": "examples/full-demo/pages/",
    "app/main.py": "examples/full-demo/main.py",
}
```

#### 0.3 Create Backward Compatibility Layer
```python
# framework/__init__.py - Maintain compatibility during migration
"""
StarModel Framework - Entity-Centric Web Framework

Now organized with Screaming Architecture:
- entities/: The heart of StarModel - entities with behavior
- events/: Event-driven interactions and commands
- realtime/: Live synchronization and broadcasting  
- reactivity/: Reactive signals and UI binding
- persistence/: Pluggable data storage backends
- infrastructure/: Technical implementation adapters
"""

# Primary API - what developers interact with
from .entities.lifecycle.entity import Entity
from .events.commands.event import event
from .persistence.backends import get_backend
from .infrastructure.web import configure_web

# Backward compatibility during migration
from .entities.lifecycle.entity import Entity as CoreEntity
from .events.commands.event import event as core_event

__all__ = ["Entity", "event", "get_backend", "configure_web"]
```

#### 0.4 Update Package Structure
```python
# pyproject.toml updates for screaming architecture
[tool.setuptools.packages.find]
where = ["framework"]
include = ["starmodel*"]

[tool.setuptools.package-dir]
starmodel = "framework"

[project.entry-points."starmodel.examples"]
counter = "examples.counter_app.main:app"
dashboard = "examples.dashboard_app.main:app"
full_demo = "examples.full_demo.main:app"
```

### **Benefits of Phase 0**
- **Immediate Clarity**: New developers instantly understand StarModel's purpose
- **Domain Focus**: Code organization reflects business capabilities, not technical layers
- **Self-Documenting**: Directory names explain what each component does
- **Foundation for Clean Architecture**: Provides proper structure for subsequent phases

---

## Phase 1: Application Service Layer Foundation

### **Objective**
Establish the core application service layer with proper dependency injection and event handling infrastructure.

### **Domain Layer Changes**

#### 1.1 Event Metadata Refinement
**Current State:** `@event` decorator mixes metadata with route registration
**Target State:** Pure metadata storage with external registration

```python
# framework/events/commands/event.py
@dataclass
class EventMetadata:
    """Clean event metadata without web coupling"""
    method_name: str
    http_method: str = "POST"
    path_template: Optional[str] = None
    selector: Optional[str] = None
    merge_type: str = "signals"
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_url_pattern(self, entity_name: str) -> str:
        """Generate URL pattern for this event"""
        if self.path_template:
            return self.path_template
        return f"/{entity_name.lower()}/{self.method_name}"

def event(
    method: str = "POST",
    path: Optional[str] = None,
    selector: Optional[str] = None,
    merge: str = "signals"
):
    """Pure metadata decorator - no route registration"""
    def decorator(func):
        # Store metadata only
        func._event_metadata = EventMetadata(
            method_name=func.__name__,
            http_method=method,
            path_template=path,
            selector=selector,
            merge_type=merge
        )
        return func
    return decorator
```

#### 1.2 Entity Base Class Cleanup
**Current State:** Entity directly references persistence backends
**Target State:** Entity requests persistence through abstraction

```python
# framework/entities/lifecycle/entity.py
class Entity(BaseModel, SignalMixin, PersistenceMixin):
    """Clean entity with no direct infrastructure dependencies"""
    
    model_config = ConfigDict(
        # Store configuration - not implementation
        store=EntityStore.SERVER_MEMORY,
        auto_persist=True,
        sync_with_client=True,
        use_namespace=False
    )
    
    @classmethod
    def get_store_config(cls) -> EntityStore:
        """Get configured storage type"""
        return cls.model_config.get("store", EntityStore.SERVER_MEMORY)
    
    @classmethod 
    def get_persistence_manager(cls) -> 'PersistenceManager':
        """Request persistence manager from DI container"""
        from starmodel.infrastructure.dependency_injection import get_persistence_manager
        return get_persistence_manager()
```

### **Application Service Layer Implementation**

#### 1.3 Event Dispatcher
**Purpose:** Central command execution with clean architecture separation

```python
# framework/events/dispatching/dispatcher.py
from typing import Any, Dict, Optional
from dataclasses import dataclass
from starmodel.entities.lifecycle.entity import Entity
from starmodel.events.commands.event import EventMetadata

@dataclass
class CommandContext:
    """Clean command context without web framework coupling"""
    entity_class: type[Entity]
    entity_id: Optional[str]
    event_name: str
    parameters: Dict[str, Any]
    user_context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass  
class CommandResult:
    """Result of command execution"""
    entity: Entity
    return_value: Any
    yielded_fragments: List[Any]
    signals_updated: Dict[str, Any]
    
class EventDispatcher:
    """Pure command dispatcher - no web framework dependencies"""
    
    def __init__(self, persistence_manager: 'PersistenceManager'):
        self.persistence_manager = persistence_manager
        
    async def dispatch_command(self, context: CommandContext) -> CommandResult:
        """Execute command in clean architecture context"""
        # 1. Load entity
        entity = await self._load_entity(context)
        
        # 2. Execute event method
        result = await self._execute_event(entity, context)
        
        # 3. Collect results
        return CommandResult(
            entity=entity,
            return_value=result.return_value,
            yielded_fragments=result.yielded_fragments,
            signals_updated=entity.get_updated_signals()
        )
    
    async def _load_entity(self, context: CommandContext) -> Entity:
        """Load entity through persistence manager"""
        backend = self.persistence_manager.get_backend(context.entity_class)
        if context.entity_id:
            return await backend.load_entity(context.entity_class, context.entity_id)
        else:
            return context.entity_class()
    
    async def _execute_event(self, entity: Entity, context: CommandContext):
        """Execute event method with parameter injection"""
        method = getattr(entity, context.event_name)
        
        # Parameter resolution
        import inspect
        sig = inspect.signature(method)
        resolved_params = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in context.parameters:
                resolved_params[param_name] = context.parameters[param_name]
        
        # Execute with collected fragments
        fragments = []
        original_method = method
        
        def fragment_collector(*args, **kwargs):
            result = original_method(*args, **kwargs)
            if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                fragments.extend(result)
            else:
                fragments.append(result)
            return result
            
        result = await fragment_collector(**resolved_params)
        
        return type('EventResult', (), {
            'return_value': result,
            'yielded_fragments': fragments
        })()
```

#### 1.4 Unit of Work Pattern
**Purpose:** Coordinate persistence and event publishing

```python
# framework/persistence/transactions/unit_of_work.py
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class DomainEvent:
    """Clean domain event representation"""
    entity_type: str
    entity_id: Optional[str]
    event_name: str
    timestamp: datetime
    payload: dict
    user_context: Optional[dict] = None

class UnitOfWork:
    """Coordinate persistence and event publishing"""
    
    def __init__(self, persistence_manager: 'PersistenceManager', event_bus: 'EventBus'):
        self.persistence_manager = persistence_manager
        self.event_bus = event_bus
        self._events: List[DomainEvent] = []
        self._entities_to_save: List[Entity] = []
    
    def add_entity(self, entity: Entity):
        """Track entity for persistence"""
        self._entities_to_save.append(entity)
    
    def add_event(self, event: DomainEvent):
        """Track domain event for publishing"""
        self._events.append(event)
    
    async def commit(self):
        """Atomic commit of all changes"""
        try:
            # 1. Persist entities
            for entity in self._entities_to_save:
                backend = self.persistence_manager.get_backend(entity.__class__)
                await backend.save_entity(entity)
            
            # 2. Publish events
            for event in self._events:
                await self.event_bus.publish(event)
                
            # 3. Clear tracking
            self._entities_to_save.clear()
            self._events.clear()
            
        except Exception as e:
            # Rollback logic here
            await self._rollback()
            raise
    
    async def _rollback(self):
        """Rollback changes if possible"""
        # Implementation depends on backend capabilities
        pass
```

#### 1.5 Event Bus Implementation
**Purpose:** Pub/sub for domain events with subscriber management

```python
# framework/events/streaming/event_bus.py
from abc import ABC, abstractmethod
from typing import Callable, List, Any
from starmodel.persistence.transactions.unit_of_work import DomainEvent

class EventBus(ABC):
    """Abstract event bus for pluggable implementations"""
    
    @abstractmethod
    async def publish(self, event: DomainEvent):
        """Publish domain event to subscribers"""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], Any]):
        """Subscribe handler to event type"""
        pass

class InProcessEventBus(EventBus):
    """In-process event bus implementation"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._global_subscribers: List[Callable] = []
    
    async def publish(self, event: DomainEvent):
        """Publish to type-specific and global subscribers"""
        event_type = f"{event.entity_type}.{event.event_name}"
        
        # Type-specific subscribers
        for handler in self._subscribers.get(event_type, []):
            await self._safe_call(handler, event)
        
        # Global subscribers  
        for handler in self._global_subscribers:
            await self._safe_call(handler, event)
    
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], Any]):
        """Subscribe to specific event type"""
        self._subscribers[event_type].append(handler)
    
    def subscribe_all(self, handler: Callable[[DomainEvent], Any]):
        """Subscribe to all events"""
        self._global_subscribers.append(handler)
    
    async def _safe_call(self, handler: Callable, event: DomainEvent):
        """Call handler with error isolation"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            # Log error but don't break other subscribers
            print(f"Event handler error: {e}")
```

#### 1.6 Dependency Injection Container
**Purpose:** Central service configuration and injection

```python
# framework/infrastructure/dependency_injection/container.py
from typing import Optional, Type, TypeVar, Dict, Any
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class ServiceConfig:
    """Service configuration"""
    implementation: type
    singleton: bool = True
    config: Dict[str, Any] = field(default_factory=dict)

class DIContainer:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, ServiceConfig] = {}
        self._instances: Dict[str, Any] = {}
    
    def register(self, service_type: Type[T], implementation: Type[T], 
                singleton: bool = True, **config):
        """Register service implementation"""
        self._services[service_type.__name__] = ServiceConfig(
            implementation=implementation,
            singleton=singleton,
            config=config
        )
    
    def get(self, service_type: Type[T]) -> T:
        """Get service instance"""
        service_name = service_type.__name__
        
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not registered")
        
        config = self._services[service_name]
        
        if config.singleton:
            if service_name not in self._instances:
                self._instances[service_name] = config.implementation(**config.config)
            return self._instances[service_name]
        else:
            return config.implementation(**config.config)

# Global container instance
_container = DIContainer()

def get_container() -> DIContainer:
    return _container

def get_persistence_manager() -> 'PersistenceManager':
    return _container.get(PersistenceManager)

def get_event_bus() -> EventBus:
    return _container.get(EventBus)
```

---

## Phase 2: Persistence Abstraction Layer

### **Objective**
Create a unified persistence abstraction that supports multiple backends through clean interfaces.

### **Implementation Details**

#### 2.1 Entity Store Configuration
**Current State:** Hardcoded backend classes
**Target State:** Configuration-driven backend selection

```python
# framework/persistence/backends/stores.py
from enum import Enum

class EntityStore(Enum):
    """Available storage backends"""
    SERVER_MEMORY = "server_memory"
    SERVER_SQL = "server_sql"  
    SERVER_REDIS = "server_redis"
    CLIENT_SESSION = "client_session"
    CLIENT_LOCAL = "client_local"
    CUSTOM = "custom"

@dataclass
class PersistenceConfig:
    """Persistence configuration for entities"""
    store: EntityStore
    ttl: Optional[int] = None
    auto_persist: bool = True
    sync_with_client: bool = True
    custom_backend: Optional[str] = None
    backend_config: Dict[str, Any] = field(default_factory=dict)
```

#### 2.2 Unified Persistence Interface
**Purpose:** Standard interface for all persistence backends

```python
# framework/persistence/repositories/interface.py
from abc import ABC, abstractmethod
from typing import Optional, Type, Any, List
from starmodel.entities.lifecycle.entity import Entity

class EntityPersistenceBackend(ABC):
    """Standard interface for all persistence backends"""
    
    @abstractmethod
    async def save_entity(self, entity: Entity, ttl: Optional[int] = None) -> str:
        """Save entity and return ID"""
        pass
    
    @abstractmethod
    async def load_entity(self, entity_class: Type[Entity], entity_id: str) -> Optional[Entity]:
        """Load entity by ID"""
        pass
    
    @abstractmethod
    async def delete_entity(self, entity_class: Type[Entity], entity_id: str) -> bool:
        """Delete entity by ID"""
        pass
    
    @abstractmethod
    async def exists(self, entity_class: Type[Entity], entity_id: str) -> bool:
        """Check if entity exists"""
        pass
    
    @abstractmethod
    async def list_entities(self, entity_class: Type[Entity], limit: int = 100) -> List[Entity]:
        """List entities of given type"""
        pass
    
    @abstractmethod
    async def cleanup_expired(self):
        """Clean up expired entities"""
        pass
```

#### 2.3 Persistence Manager
**Purpose:** Factory and coordinator for all persistence backends

```python
# framework/persistence/repositories/manager.py
from typing import Dict, Type, Optional
from starmodel.entities.lifecycle.entity import Entity
from starmodel.persistence.backends.stores import EntityStore
from starmodel.persistence.repositories.interface import EntityPersistenceBackend

class PersistenceManager:
    """Factory and coordinator for persistence backends"""
    
    def __init__(self):
        self._backends: Dict[EntityStore, EntityPersistenceBackend] = {}
        self._entity_backends: Dict[Type[Entity], EntityPersistenceBackend] = {}
    
    def register_backend(self, store_type: EntityStore, backend: EntityPersistenceBackend):
        """Register backend for store type"""
        self._backends[store_type] = backend
    
    def get_backend(self, entity_class: Type[Entity]) -> EntityPersistenceBackend:
        """Get backend for entity class"""
        # Check cached mapping
        if entity_class in self._entity_backends:
            return self._entity_backends[entity_class]
        
        # Resolve from entity configuration
        store_type = entity_class.get_store_config()
        
        if store_type not in self._backends:
            raise ValueError(f"No backend registered for store type: {store_type}")
        
        backend = self._backends[store_type]
        self._entity_backends[entity_class] = backend
        return backend
    
    async def initialize_all(self):
        """Initialize all registered backends"""
        for backend in self._backends.values():
            if hasattr(backend, 'initialize'):
                await backend.initialize()
```

#### 2.4 Enhanced Memory Backend
**Current State:** Basic in-memory storage
**Target State:** Feature-complete with TTL and cleanup

```python
# framework/persistence/backends/memory.py
from typing import Dict, Optional, Type, List, Any
from datetime import datetime, timedelta
import asyncio
from starmodel.entities.lifecycle.entity import Entity
from starmodel.persistence.repositories.interface import EntityPersistenceBackend

class MemoryEntityBackend(EntityPersistenceBackend):
    """Enhanced memory backend with TTL and cleanup"""
    
    def __init__(self, cleanup_interval: int = 300):
        self._storage: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Start cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def save_entity(self, entity: Entity, ttl: Optional[int] = None) -> str:
        """Save entity with optional TTL"""
        entity_id = getattr(entity, 'id', None) or self._generate_id(entity)
        key = self._make_key(entity.__class__, entity_id)
        
        # Store entity instance (not serialized)
        self._storage[key] = entity
        
        # Set expiry if TTL provided
        if ttl:
            self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
        
        return entity_id
    
    async def load_entity(self, entity_class: Type[Entity], entity_id: str) -> Optional[Entity]:
        """Load entity by ID"""
        key = self._make_key(entity_class, entity_id)
        
        # Check expiry
        if key in self._expiry and datetime.now() > self._expiry[key]:
            del self._storage[key]
            del self._expiry[key]
            return None
        
        return self._storage.get(key)
    
    async def delete_entity(self, entity_class: Type[Entity], entity_id: str) -> bool:
        """Delete entity"""
        key = self._make_key(entity_class, entity_id)
        if key in self._storage:
            del self._storage[key]
            self._expiry.pop(key, None)
            return True
        return False
    
    async def exists(self, entity_class: Type[Entity], entity_id: str) -> bool:
        """Check existence"""
        entity = await self.load_entity(entity_class, entity_id)
        return entity is not None
    
    async def list_entities(self, entity_class: Type[Entity], limit: int = 100) -> List[Entity]:
        """List entities of type"""
        prefix = f"{entity_class.__name__}:"
        entities = []
        
        for key, entity in self._storage.items():
            if key.startswith(prefix) and isinstance(entity, entity_class):
                entities.append(entity)
                if len(entities) >= limit:
                    break
        
        return entities
    
    async def cleanup_expired(self):
        """Remove expired entities"""
        now = datetime.now()
        expired_keys = [key for key, expiry in self._expiry.items() if now > expiry]
        
        for key in expired_keys:
            self._storage.pop(key, None)
            self._expiry.pop(key, None)
    
    def _make_key(self, entity_class: Type[Entity], entity_id: str) -> str:
        """Generate storage key"""
        return f"{entity_class.__name__}:{entity_id}"
    
    def _generate_id(self, entity: Entity) -> str:
        """Generate ID for entity"""
        import uuid
        return str(uuid.uuid4())
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Cleanup error: {e}")
```

#### 2.5 Entity Persistence Integration
**Purpose:** Update Entity class to use persistence manager

```python
# framework/entities/lifecycle/entity.py (updated)
class Entity(BaseModel, SignalMixin):
    """Entity with persistence manager integration"""
    
    id: Optional[str] = None
    
    async def save(self, ttl: Optional[int] = None) -> str:
        """Save entity through persistence manager"""
        manager = self.get_persistence_manager()
        backend = manager.get_backend(self.__class__)
        self.id = await backend.save_entity(self, ttl)
        return self.id
    
    @classmethod
    async def get(cls, entity_id: str) -> Optional['Entity']:
        """Load entity by ID"""
        manager = cls.get_persistence_manager()
        backend = manager.get_backend(cls)
        return await backend.load_entity(cls, entity_id)
    
    async def delete(self) -> bool:
        """Delete this entity"""
        if not self.id:
            return False
        manager = self.get_persistence_manager()
        backend = manager.get_backend(self.__class__)
        return await backend.delete_entity(self.__class__, self.id)
    
    @classmethod
    async def list_all(cls, limit: int = 100) -> List['Entity']:
        """List all entities of this type"""
        manager = cls.get_persistence_manager()  
        backend = manager.get_backend(cls)
        return await backend.list_entities(cls, limit)
```

---

## Phase 3: Web Adapter Decoupling

### **Objective**
Decouple FastHTML/Datastar specifics from core logic, enabling pluggable web frameworks and real-time mechanisms.

### **Implementation Details**

#### 3.1 Web Adapter Interface
**Purpose:** Abstract web framework integration

```python
# framework/infrastructure/web/interface.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass

@dataclass
class WebRequest:
    """Framework-agnostic request representation"""
    method: str
    path: str
    query_params: Dict[str, Any]
    form_data: Dict[str, Any]
    headers: Dict[str, str]
    user_context: Optional[Dict[str, Any]] = None

@dataclass  
class WebResponse:
    """Framework-agnostic response representation"""
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    content: Any = None
    content_type: str = "application/json"

class WebAdapter(ABC):
    """Interface for web framework integration"""
    
    @abstractmethod
    def register_entity_routes(self, entity_class: type, dispatcher: 'EventDispatcher'):
        """Register routes for entity events"""
        pass
    
    @abstractmethod
    def extract_request_context(self, framework_request: Any) -> WebRequest:
        """Convert framework request to standard format"""
        pass
    
    @abstractmethod
    def create_response(self, web_response: WebResponse) -> Any:
        """Convert standard response to framework format"""
        pass
```

#### 3.2 FastHTML Adapter Implementation
**Purpose:** Concrete FastHTML integration without coupling

```python
# framework/infrastructure/web/fasthtml_adapter.py
from typing import Any, Dict
from fasthtml.common import Request, StreamingResponse
from starmodel.infrastructure.web.interface import WebAdapter, WebRequest, WebResponse
from starmodel.events.dispatching.dispatcher import EventDispatcher, CommandContext

class FastHTMLAdapter(WebAdapter):
    """FastHTML-specific web adapter"""
    
    def __init__(self, router: Any):
        self.router = router
    
    def register_entity_routes(self, entity_class: type, dispatcher: EventDispatcher):
        """Register FastHTML routes for entity events"""
        entity_name = entity_class.__name__.lower()
        
        # Scan for @event methods
        for attr_name in dir(entity_class):
            attr = getattr(entity_class, attr_name)
            if hasattr(attr, '_event_metadata'):
                metadata = attr._event_metadata
                
                # Create route path
                path = metadata.to_url_pattern(entity_name)
                
                # Create handler
                handler = self._create_event_handler(
                    entity_class, metadata.method_name, dispatcher
                )
                
                # Register with FastHTML router
                self.router.add_route(
                    path=path,
                    endpoint=handler,
                    methods=[metadata.http_method]
                )
    
    def _create_event_handler(self, entity_class: type, event_name: str, dispatcher: EventDispatcher):
        """Create FastHTML route handler"""
        async def handler(request: Request):
            # Convert to standard format
            web_request = self.extract_request_context(request)
            
            # Create command context
            context = CommandContext(
                entity_class=entity_class,
                entity_id=web_request.query_params.get('id'),
                event_name=event_name,
                parameters=web_request.form_data or web_request.query_params,
                user_context=web_request.user_context
            )
            
            # Dispatch command
            result = await dispatcher.dispatch_command(context)
            
            # Let response formatter handle the result
            return await self._format_response(result, web_request)
        
        return handler
    
    def extract_request_context(self, request: Request) -> WebRequest:
        """Extract context from FastHTML request"""
        return WebRequest(
            method=request.method,
            path=str(request.url.path),
            query_params=dict(request.query_params),
            form_data=self._extract_form_data(request),
            headers=dict(request.headers),
            user_context=self._extract_user_context(request)
        )
    
    def _extract_form_data(self, request: Request) -> Dict[str, Any]:
        """Extract form data from request"""
        # Implementation depends on FastHTML's form handling
        # This is where FastHTML-specific parsing goes
        pass
    
    async def _format_response(self, result, web_request: WebRequest):
        """Format response for FastHTML"""
        # This is where Datastar SSE formatting would go
        # But it's isolated to this adapter
        pass
```

#### 3.3 Real-time Response Formatting
**Purpose:** Pluggable response formatting for different real-time mechanisms

```python
# framework/realtime/protocols/response_formatters.py
from abc import ABC, abstractmethod
from typing import Any
from starmodel.events.dispatching.dispatcher import CommandResult
from starmodel.infrastructure.web.interface import WebRequest, WebResponse

class ResponseFormatter(ABC):
    """Abstract response formatter"""
    
    @abstractmethod
    async def format_response(self, result: CommandResult, request: WebRequest) -> WebResponse:
        """Format command result for client"""
        pass

class DatastarSSEFormatter(ResponseFormatter):
    """Datastar SSE response formatter"""
    
    async def format_response(self, result: CommandResult, request: WebRequest) -> WebResponse:
        """Format as Datastar SSE stream"""
        async def generate_sse():
            # Yield signals update
            if result.signals_updated:
                yield f"data: {json.dumps({'signals': result.signals_updated})}\n\n"
            
            # Yield fragments
            for fragment in result.yielded_fragments:
                if hasattr(fragment, 'render'):  # FastHTML component
                    html = fragment.render()
                    yield f"data: {json.dumps({'fragment': html})}\n\n"
        
        # Return streaming response
        return WebResponse(
            content=generate_sse(),
            content_type="text/event-stream",
            headers={"Cache-Control": "no-cache"}
        )

class JSONResponseFormatter(ResponseFormatter):
    """Simple JSON response formatter"""
    
    async def format_response(self, result: CommandResult, request: WebRequest) -> WebResponse:
        """Format as JSON response"""
        return WebResponse(
            content={
                "success": True,
                "signals": result.signals_updated,
                "fragments": [str(f) for f in result.yielded_fragments]
            },
            content_type="application/json"
        )
```

#### 3.4 Event Bus Integration for Real-time Updates
**Purpose:** Decouple real-time updates from request/response cycle

```python
# framework/realtime/broadcasting/sse_broadcaster.py
from starmodel.events.streaming.event_bus import EventBus, DomainEvent
from starmodel.realtime.protocols.response_formatters import ResponseFormatter

class SSEBroadcaster:
    """Broadcast domain events via SSE"""
    
    def __init__(self, event_bus: EventBus, formatter: ResponseFormatter):
        self.event_bus = event_bus
        self.formatter = formatter
        self.connections: Dict[str, Any] = {}
    
    def start(self):
        """Start listening to event bus"""
        self.event_bus.subscribe_all(self.handle_domain_event)
    
    async def handle_domain_event(self, event: DomainEvent):
        """Broadcast event to connected clients"""
        # Convert domain event to command result
        result = self._domain_event_to_result(event)
        
        # Format for SSE
        response = await self.formatter.format_response(result, None)
        
        # Broadcast to relevant connections
        await self._broadcast_to_connections(response, event)
    
    def _domain_event_to_result(self, event: DomainEvent) -> CommandResult:
        """Convert domain event back to command result for formatting"""
        # Implementation depends on event payload structure
        pass
    
    async def _broadcast_to_connections(self, response: WebResponse, event: DomainEvent):
        """Send response to connected SSE clients"""
        # Implementation depends on connection management
        pass
```

---

## Phase 4: SQL Integration Cleanup

### **Objective**
Clean up SQL integration to avoid inheritance conflicts and make SQL truly optional.

### **Implementation Details**

#### 4.1 SQL Backend Implementation
**Purpose:** Clean SQL backend without inheritance conflicts

```python
# framework/persistence/backends/sql.py
from typing import Optional, Type, List, Any, Dict
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel, select
from starmodel.entities.lifecycle.entity import Entity
from starmodel.persistence.repositories.interface import EntityPersistenceBackend

class SQLModelBackend(EntityPersistenceBackend):
    """SQLModel persistence backend"""
    
    def __init__(self, database_url: str = "sqlite:///starmodel.db"):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._table_registry: Dict[Type[Entity], Type[SQLModel]] = {}
    
    async def initialize(self):
        """Initialize database tables"""
        SQLModel.metadata.create_all(self.engine)
    
    def register_entity_table(self, entity_class: Type[Entity], table_class: Type[SQLModel]):
        """Register entity-to-table mapping"""
        self._table_registry[entity_class] = table_class
    
    async def save_entity(self, entity: Entity, ttl: Optional[int] = None) -> str:
        """Save entity to SQL database"""
        table_class = self._get_table_class(entity.__class__)
        
        with self.SessionLocal() as session:
            # Convert entity to table model
            table_instance = self._entity_to_table(entity, table_class)
            
            # Save to database
            session.add(table_instance)
            session.commit()
            session.refresh(table_instance)
            
            return str(table_instance.id)
    
    async def load_entity(self, entity_class: Type[Entity], entity_id: str) -> Optional[Entity]:
        """Load entity from SQL database"""
        table_class = self._get_table_class(entity_class)
        
        with self.SessionLocal() as session:
            statement = select(table_class).where(table_class.id == entity_id)
            table_instance = session.exec(statement).first()
            
            if table_instance:
                return self._table_to_entity(table_instance, entity_class)
            return None
    
    async def delete_entity(self, entity_class: Type[Entity], entity_id: str) -> bool:
        """Delete entity from database"""
        table_class = self._get_table_class(entity_class)
        
        with self.SessionLocal() as session:
            statement = select(table_class).where(table_class.id == entity_id)
            table_instance = session.exec(statement).first()
            
            if table_instance:
                session.delete(table_instance)
                session.commit()
                return True
            return False
    
    async def exists(self, entity_class: Type[Entity], entity_id: str) -> bool:
        """Check if entity exists"""
        entity = await self.load_entity(entity_class, entity_id)
        return entity is not None
    
    async def list_entities(self, entity_class: Type[Entity], limit: int = 100) -> List[Entity]:
        """List entities from database"""
        table_class = self._get_table_class(entity_class)
        
        with self.SessionLocal() as session:
            statement = select(table_class).limit(limit)
            table_instances = session.exec(statement).all()
            
            return [self._table_to_entity(t, entity_class) for t in table_instances]
    
    async def cleanup_expired(self):
        """No TTL support in basic SQL backend"""
        pass
    
    def _get_table_class(self, entity_class: Type[Entity]) -> Type[SQLModel]:
        """Get SQLModel table class for entity"""
        if entity_class not in self._table_registry:
            raise ValueError(f"No table registered for entity: {entity_class.__name__}")
        return self._table_registry[entity_class]
    
    def _entity_to_table(self, entity: Entity, table_class: Type[SQLModel]) -> SQLModel:
        """Convert entity to table model"""
        # Copy fields from entity to table model
        entity_data = entity.model_dump()
        return table_class(**entity_data)
    
    def _table_to_entity(self, table_instance: SQLModel, entity_class: Type[Entity]) -> Entity:
        """Convert table model to entity"""
        # Copy fields from table model to entity
        table_data = table_instance.model_dump()
        return entity_class(**table_data)
```

#### 4.2 SQL Entity Registration Pattern
**Purpose:** Clean way to register SQL entities without inheritance issues

```python
# framework/persistence/backends/sql_registry.py
from typing import Type
from sqlmodel import SQLModel, Field
from starmodel.entities.lifecycle.entity import Entity
from starmodel.persistence.backends.sql import SQLModelBackend

def create_sql_table(entity_class: Type[Entity], table_name: Optional[str] = None) -> Type[SQLModel]:
    """Create SQLModel table class for entity"""
    table_name = table_name or entity_class.__name__.lower()
    
    # Get entity fields
    entity_fields = entity_class.model_fields
    
    # Create table class dynamically
    table_fields = {}
    for field_name, field_info in entity_fields.items():
        if field_name == 'id':
            table_fields[field_name] = Field(primary_key=True)
        else:
            table_fields[field_name] = field_info
    
    # Create SQLModel class
    table_class = type(
        f"{entity_class.__name__}Table",
        (SQLModel,),
        {
            **table_fields,
            "__tablename__": table_name,
            "__table_args__": {"extend_existing": True}
        }
    )
    
    return table_class

def register_sql_entity(entity_class: Type[Entity], backend: SQLModelBackend, 
                       table_name: Optional[str] = None):
    """Register entity with SQL backend"""
    table_class = create_sql_table(entity_class, table_name)
    backend.register_entity_table(entity_class, table_class)
    return table_class

# Usage example:
# register_sql_entity(User, sql_backend)
# register_sql_entity(Product, sql_backend, "products")
```

#### 4.3 SQL Entity Usage Pattern
**Purpose:** Clean usage pattern for SQL entities

```python
# Example entity definition
class User(Entity):
    """User entity with SQL persistence"""
    name: str
    email: str
    age: int = 0
    
    model_config = {
        "store": EntityStore.SERVER_SQL
    }
    
    @event
    async def update_profile(self, name: str, email: str):
        """Update user profile"""
        self.name = name
        self.email = email

# Registration in app setup
def configure_sql_entities(sql_backend: SQLModelBackend):
    """Register all SQL entities"""
    register_sql_entity(User, sql_backend)
    register_sql_entity(Product, sql_backend)
    # etc.
```

---

## Implementation Strategy

### **Phase Dependencies**
1. **Phase 1 (Application Service Layer)** - Must be completed first as it provides the foundation
2. **Phase 2 (Persistence Abstraction)** - Depends on Phase 1's DI container
3. **Phase 3 (Web Adapter Decoupling)** - Can be done in parallel with Phase 2
4. **Phase 4 (SQL Integration)** - Depends on Phase 2's persistence abstraction

### **Migration Path**
1. **Backward Compatibility**: Each phase maintains backward compatibility with existing code
2. **Gradual Migration**: Old patterns work while new patterns are available
3. **Feature Flags**: Use configuration to enable new architecture components gradually
4. **Testing Strategy**: Comprehensive tests for each phase before moving to the next

### **Success Criteria**

#### **Phase 1 Success Criteria**
- [ ] Event dispatcher can execute events without direct web framework dependencies
- [ ] Unit of Work coordinates persistence and event publishing
- [ ] Event Bus publishes domain events to subscribers
- [ ] DI container provides configurable service resolution
- [ ] All existing functionality preserved

#### **Phase 2 Success Criteria**  
- [ ] Persistence Manager can switch backends via configuration
- [ ] Multiple persistence backends can coexist
- [ ] Entity classes don't directly reference backend implementations
- [ ] Memory backend has TTL and cleanup capabilities
- [ ] New backends can be added without changing entity code

#### **Phase 3 Success Criteria**
- [ ] FastHTML adapter isolated from core logic
- [ ] Response formatting is pluggable
- [ ] Event Bus can drive real-time updates independently
- [ ] New web frameworks can be supported via adapters
- [ ] Real-time mechanisms are swappable

#### **Phase 4 Success Criteria**
- [ ] SQL persistence works without inheritance conflicts
- [ ] SQL is truly optional (no loading if unused)
- [ ] SQL entities work with the same API as memory entities
- [ ] Multiple SQL entities can share the same backend
- [ ] SQL backend supports standard CRUD operations

### **Quality Gates**
- All existing tests pass after each phase
- New functionality has comprehensive test coverage
- Documentation is updated for each phase
- Performance benchmarks show no regression
- Memory usage remains stable

## **Integrated Architecture Summary**

This refactoring plan transforms StarModel by integrating **Screaming Architecture** with **Clean Architecture** principles, creating a framework that is both self-documenting and architecturally sound.

### **Before vs After Transformation**

#### **Current State (Framework-Centric)**
```
src/starmodel/
├── core/              # What does this do?
├── app/               # What kind of app?
├── persistence/       # For what data?
├── web/               # What web functionality?
└── adapters/          # Adapting what to what?
```
*Problems: Generic names, unclear purpose, framework-focused organization*

#### **Target State (Domain-Centric + Clean Architecture)**
```
framework/                          # StarModel Framework
├── entities/                      # 🎯 ENTITY-CENTRIC DESIGN
│   ├── lifecycle/                 # Domain: Entity management
│   ├── behavior/                  # Domain: @event methods & business logic
│   ├── composition/               # Domain: Relationships & aggregates
│   └── validation/                # Domain: Business rules & constraints
│
├── events/                        # 🚀 EVENT-DRIVEN INTERACTIONS
│   ├── commands/                  # Application: Command definitions
│   ├── handlers/                  # Application: Event processing
│   ├── dispatching/               # Application: Command coordination
│   └── streaming/                 # Application: Event bus & pub/sub
│
├── realtime/                      # ⚡ LIVE COLLABORATION
│   ├── synchronization/           # Application: State sync logic
│   ├── broadcasting/              # Application: Multi-user events
│   ├── connections/               # Infrastructure: Connection mgmt
│   └── protocols/                 # Infrastructure: SSE, WebSocket
│
├── reactivity/                    # 🔄 REACTIVE UI UPDATES
│   ├── signals/                   # Domain: Reactive state
│   ├── binding/                   # Application: UI binding logic
│   ├── updates/                   # Application: Update coordination
│   └── subscriptions/             # Infrastructure: Change detection
│
├── persistence/                   # 💾 DATA MANAGEMENT
│   ├── backends/                  # Infrastructure: Storage adapters
│   ├── repositories/              # Application: Data access patterns
│   ├── transactions/              # Application: ACID operations
│   └── caching/                   # Infrastructure: Performance
│
└── infrastructure/                # 🔧 TECHNICAL ADAPTERS
    ├── web/                       # Infrastructure: Framework adapters
    ├── storage/                   # Infrastructure: DB connections
    ├── messaging/                 # Infrastructure: Event buses
    └── deployment/                # Infrastructure: Configuration
```
*Benefits: Self-documenting, domain-focused, clean architecture boundaries*

### **Clean Architecture Mapping**

#### **Domain Layer (Pure Business Logic)**
- `entities/lifecycle/` - Core entity definitions
- `entities/behavior/` - Business logic and @event methods
- `entities/composition/` - Domain relationships
- `reactivity/signals/` - Reactive domain state

#### **Application Layer (Use Cases & Coordination)**
- `events/dispatching/` - Command coordination
- `events/handlers/` - Use case implementations
- `persistence/transactions/` - Data coordination
- `realtime/synchronization/` - Real-time coordination

#### **Infrastructure Layer (Technical Implementation)**
- `infrastructure/web/` - Web framework adapters
- `infrastructure/storage/` - Database adapters
- `persistence/backends/` - Storage implementations
- `realtime/protocols/` - Real-time protocols

### **Developer Experience Impact**

#### **What Developers See (API Layer)**
```python
# Simple, domain-focused imports
from starmodel.entities import Entity, event
from starmodel.persistence import configure_backends
from starmodel.realtime import enable_collaboration

# Self-explanatory entity definition
class ChatRoom(Entity):
    messages: List[str] = []
    participants: List[str] = []
    
    model_config = {
        "store": "sql",           # Persistence choice
        "realtime": True,         # Real-time updates
        "collaborative": True,    # Multi-user support
    }
    
    @event(description="Send message to room")
    async def send_message(self, message: str, user: str):
        self.messages.append(f"{user}: {message}")
        # Automatically synced to all connected clients
```

#### **What Framework Provides (Implementation Layer)**
```python
# Framework handles all the complex coordination
# - Command dispatching via events/dispatching/
# - Persistence via persistence/backends/
# - Real-time sync via realtime/synchronization/
# - UI updates via reactivity/signals/
# - Multi-user coordination via realtime/broadcasting/
```

### **Migration Benefits**

#### **Immediate Clarity**
- New developers instantly understand: "This is about entities with events that work in real-time"
- Domain concepts are front-and-center, not hidden behind technical abstractions
- Code organization matches mental model of the problem domain

#### **Architectural Soundness**
- Clean separation between domain, application, and infrastructure
- Dependency inversion ensures domain doesn't depend on infrastructure
- Plugin architecture enables swapping components without affecting core logic

#### **Maintainability**
- Related functionality grouped by purpose, not technology
- Clear boundaries make testing and modification easier
- Self-documenting structure reduces onboarding time

#### **Extensibility**
- Clear extension points for new backends, protocols, and frameworks
- Plugin architecture supports adding capabilities without core changes
- Multiple deployment strategies supported through adapter swapping

### **Implementation Roadmap**

#### **Phase 0: Foundation (Week 1)**
- Create screaming architecture directory structure
- Establish file migration mapping
- Create backward compatibility layer
- Begin gradual file migration

#### **Phase 1: Clean Architecture Core (Week 2-3)**
- Implement application service layer (dispatching, UoW, event bus)
- Create dependency injection infrastructure
- Establish clean domain/application/infrastructure boundaries

#### **Phase 2: Persistence Abstraction (Week 4)**
- Implement unified persistence interface
- Create pluggable backend system
- Enable configuration-driven backend selection

#### **Phase 3: Web Decoupling (Week 5)**
- Abstract web framework integration
- Create pluggable response formatting
- Enable real-time mechanism swapping

#### **Phase 4: SQL Integration (Week 6)**
- Clean up SQL inheritance conflicts
- Make SQL truly optional
- Complete plugin architecture

### **Success Metrics**

#### **Developer Experience**
- ✅ New developer can understand StarModel's purpose in < 30 seconds
- ✅ Entity definition remains simple (< 10 lines for basic functionality)
- ✅ Framework provides "batteries included" defaults
- ✅ Advanced customization possible without core modifications

#### **Architectural Quality**
- ✅ Domain logic has zero infrastructure dependencies
- ✅ Any component can be swapped without affecting others
- ✅ Test coverage maintained throughout migration
- ✅ Performance remains stable or improves

#### **Code Organization**
- ✅ Related functionality grouped by domain purpose
- ✅ Import paths immediately communicate intent
- ✅ New features have obvious places to live
- ✅ Plugin development is straightforward

This integrated approach transforms StarModel from a generic framework into a **self-documenting, domain-driven platform** that immediately communicates its unique value: **"Entity-centric, event-driven, real-time collaborative applications with clean architecture."**