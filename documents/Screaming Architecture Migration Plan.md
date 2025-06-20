# StarModel Screaming Architecture Migration Plan

## Migration Overview

This document provides a step-by-step plan to migrate StarModel from its current framework-centric structure to a domain-centric Screaming Architecture without breaking existing functionality.

## Migration Strategy

### **Safe Migration Principles**
1. **Non-Breaking**: Maintain backward compatibility throughout
2. **Gradual**: Move files incrementally, not all at once
3. **Testable**: Ensure all functionality works after each step
4. **Reversible**: Each step can be undone if issues arise

### **Migration Phases**
```
Phase 1: Prepare New Structure (Week 1)
    ↓
Phase 2: Core Components Migration (Week 2-3)
    ↓  
Phase 3: Infrastructure Migration (Week 4)
    ↓
Phase 4: Demo Apps Reorganization (Week 5)
    ↓
Phase 5: Import Path Updates & Cleanup (Week 6)
```

---

## Phase 1: Prepare New Structure

### **1.1 Create Directory Structure**
Create the new screaming architecture directories alongside existing structure:

```bash
# Create framework directory structure
mkdir -p framework/{entities,events,realtime,reactivity,persistence,interactions,collaboration,infrastructure}
mkdir -p framework/entities/{lifecycle,behavior,composition,validation}
mkdir -p framework/events/{commands,handlers,dispatching,streaming}
mkdir -p framework/realtime/{synchronization,broadcasting,connections,protocols}
mkdir -p framework/reactivity/{signals,binding,updates,subscriptions}
mkdir -p framework/persistence/{backends,repositories,transactions,caching}
mkdir -p framework/interactions/{components,pages,forms,navigation}
mkdir -p framework/collaboration/{sessions,permissions,sharing,conflicts}
mkdir -p framework/infrastructure/{web,storage,messaging,security,deployment}

# Create examples directory structure
mkdir -p examples/{counter-app,dashboard-app,collaboration-app,full-demo}
mkdir -p examples/counter-app/{entities,pages}
mkdir -p examples/dashboard-app/{entities,pages}
mkdir -p examples/collaboration-app/{entities,pages}
mkdir -p examples/full-demo/{entities,pages}

# Create tools directory structure
mkdir -p tools/{cli,scaffolding,migration,testing}
```

### **1.2 Create Compatibility Layer**
Create `__init__.py` files that maintain backward compatibility:

```python
# framework/__init__.py
"""
StarModel Framework - Screaming Architecture
Maintains backward compatibility during migration
"""

# Re-export from old locations for compatibility
from .entities.lifecycle.entity import Entity
from .events.commands.event import event
from .persistence.backends.memory import MemoryBackend
from .infrastructure.web.fasthtml_adapter import FastHTMLAdapter

# Legacy compatibility imports
from .entities.lifecycle import Entity as CoreEntity
from .events.commands import event as CoreEvent

__all__ = [
    "Entity", "event", "MemoryBackend", "FastHTMLAdapter",
    "CoreEntity", "CoreEvent"  # Legacy names
]
```

### **1.3 Create Migration Tracking**
```python
# tools/migration/tracker.py
"""Track migration progress and validate completeness"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

@dataclass
class FileMapping:
    old_path: str
    new_path: str
    migrated: bool = False
    tested: bool = False
    
class MigrationTracker:
    def __init__(self):
        self.mappings: List[FileMapping] = []
        self.load_migration_plan()
    
    def load_migration_plan(self):
        """Load the complete file migration mapping"""
        self.mappings = [
            # Core Entity System
            FileMapping("src/starmodel/core/entity.py", "framework/entities/lifecycle/entity.py"),
            FileMapping("src/starmodel/core/events.py", "framework/events/commands/event.py"),
            FileMapping("src/starmodel/core/signals.py", "framework/reactivity/signals/signal_system.py"),
            
            # Application Layer
            FileMapping("src/starmodel/app/dispatcher.py", "framework/events/dispatching/dispatcher.py"),
            FileMapping("src/starmodel/app/bus.py", "framework/events/streaming/event_streams.py"),
            FileMapping("src/starmodel/app/uow.py", "framework/persistence/transactions/unit_of_work.py"),
            
            # Persistence Layer
            FileMapping("src/starmodel/persistence/memory.py", "framework/persistence/backends/memory.py"),
            FileMapping("src/starmodel/persistence/sql.py", "framework/persistence/backends/sql.py"),
            FileMapping("src/starmodel/persistence/base.py", "framework/persistence/repositories/base.py"),
            
            # Web Infrastructure
            FileMapping("src/starmodel/adapters/fasthtml.py", "framework/infrastructure/web/fasthtml_adapter.py"),
            FileMapping("src/starmodel/web/", "framework/infrastructure/web/"),
            
            # Demo Applications
            FileMapping("app/entities/", "examples/full-demo/entities/"),
            FileMapping("app/pages/", "examples/full-demo/pages/"),
            FileMapping("app/main.py", "examples/full-demo/main.py"),
        ]
    
    def mark_migrated(self, old_path: str):
        """Mark a file as successfully migrated"""
        for mapping in self.mappings:
            if mapping.old_path == old_path:
                mapping.migrated = True
                break
    
    def get_migration_status(self) -> Dict[str, int]:
        """Get overall migration status"""
        total = len(self.mappings)
        migrated = sum(1 for m in self.mappings if m.migrated)
        tested = sum(1 for m in self.mappings if m.tested)
        
        return {
            "total_files": total,
            "migrated": migrated,
            "tested": tested,
            "remaining": total - migrated,
        }
```

---

## Phase 2: Core Components Migration

### **2.1 Migrate Entity System**

#### **Step 2.1.1: Move Core Entity**
```bash
# Copy and enhance entity.py
cp src/starmodel/core/entity.py framework/entities/lifecycle/entity.py
```

```python
# framework/entities/lifecycle/entity.py
"""
Entity Lifecycle Management - The Heart of StarModel

This module contains the core Entity class that represents the fundamental
building block of StarModel applications. Entities are domain objects with
behavior, state, and event-driven interactions.
"""
from typing import Optional, Dict, Any, List, Type
from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Import from other screaming architecture modules
from ...reactivity.signals.signal_system import SignalMixin
from ...persistence.repositories.base import PersistenceMixin
from ...events.commands.event import EventCapable

class Entity(BaseModel, SignalMixin, PersistenceMixin, EventCapable):
    """
    Core Entity class - represents a domain object with behavior.
    
    Entities are the heart of StarModel applications. They:
    - Contain both data and behavior (@event methods)
    - Support reactive signals for UI binding
    - Handle their own persistence through backends
    - Enable real-time collaboration
    """
    
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        # Domain configuration (not technical implementation)
        store="memory",  # Where to persist: memory, sql, redis, client
        realtime=True,   # Enable real-time synchronization
        collaborative=False,  # Enable multi-user collaboration
        signals=True,    # Enable reactive signals
        validate_assignment=True,
        extra="forbid"
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.created_at:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    async def save(self, **kwargs) -> str:
        """Save entity through appropriate persistence backend"""
        self.updated_at = datetime.now()
        return await super().save(**kwargs)
    
    @classmethod
    def domain_name(cls) -> str:
        """Get domain name for this entity type"""
        return cls.__name__
    
    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

# Backward compatibility
CoreEntity = Entity  # For migration period
```

#### **Step 2.1.2: Create Entity Behavior Module**
```python
# framework/entities/behavior/events.py
"""
Entity Event Behavior - @event decorator and event handling

This module defines how entities can have interactive behavior through
the @event decorator pattern.
"""
from typing import Callable, Any, Dict, Optional
from functools import wraps
from dataclasses import dataclass

@dataclass
class EventMetadata:
    """Metadata for entity event methods"""
    name: str
    description: Optional[str] = None
    http_method: str = "POST"
    realtime: bool = True
    permissions: Optional[List[str]] = None
    
class EventCapable:
    """Mixin for entities that can have @event methods"""
    
    @classmethod
    def get_events(cls) -> Dict[str, EventMetadata]:
        """Get all @event methods on this entity"""
        events = {}
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_event_metadata'):
                events[attr_name] = attr._event_metadata
        return events
    
    def get_event_method(self, event_name: str) -> Optional[Callable]:
        """Get event method by name"""
        if event_name in self.get_events():
            return getattr(self, event_name)
        return None

def event(description: Optional[str] = None, method: str = "POST", 
          realtime: bool = True, permissions: Optional[List[str]] = None):
    """
    Mark a method as an interactive event.
    
    Events are the primary way users interact with entities.
    They automatically become:
    - HTTP endpoints for web interactions
    - Real-time synchronized actions
    - UI-bound interactive elements
    """
    def decorator(func: Callable) -> Callable:
        # Store event metadata
        func._event_metadata = EventMetadata(
            name=func.__name__,
            description=description,
            http_method=method,
            realtime=realtime,
            permissions=permissions
        )
        
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Pre-event processing
            await self._before_event(func.__name__, args, kwargs)
            
            # Execute event
            result = await func(self, *args, **kwargs)
            
            # Post-event processing
            await self._after_event(func.__name__, result)
            
            return result
            
        return wrapper
    return decorator
```

#### **Step 2.1.3: Update Import Compatibility**
```python
# framework/entities/__init__.py
"""
Entity System - The Heart of StarModel

Entities are domain objects that contain both data and behavior.
They are the primary building blocks of StarModel applications.
"""

# Primary exports
from .lifecycle.entity import Entity
from .behavior.events import event, EventCapable
from .validation.constraints import validate_entity
from .composition.relationships import related_to, has_many

# Backward compatibility during migration
from .lifecycle.entity import Entity as CoreEntity
from .behavior.events import event as core_event

__all__ = [
    "Entity", "event", "EventCapable", "validate_entity",
    "related_to", "has_many",
    # Legacy compatibility
    "CoreEntity", "core_event"
]
```

### **2.2 Migrate Event System**

#### **Step 2.2.1: Move Event Dispatcher**
```bash
cp src/starmodel/app/dispatcher.py framework/events/dispatching/dispatcher.py
```

```python
# framework/events/dispatching/dispatcher.py
"""
Event Command Dispatching - Central Command Execution

The dispatcher is responsible for:
- Routing commands to appropriate entity methods
- Managing command execution lifecycle
- Coordinating with persistence and real-time systems
"""
from typing import Any, Dict, Optional, Type
from dataclasses import dataclass
from datetime import datetime

from ...entities.lifecycle.entity import Entity
from ...persistence.transactions.unit_of_work import UnitOfWork
from ...realtime.synchronization.state_sync import StateSynchronizer

@dataclass
class CommandRequest:
    """A command request to execute an entity event"""
    entity_type: str
    entity_id: Optional[str]
    event_name: str
    parameters: Dict[str, Any]
    user_context: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None

@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    entity: Optional[Entity]
    return_value: Any
    error: Optional[str] = None
    signals_updated: Dict[str, Any] = None
    fragments_generated: List[Any] = None

class EventDispatcher:
    """
    Central dispatcher for entity events.
    
    This is the heart of StarModel's command processing.
    It coordinates between entities, persistence, and real-time systems.
    """
    
    def __init__(self, unit_of_work: UnitOfWork, synchronizer: StateSynchronizer):
        self.unit_of_work = unit_of_work
        self.synchronizer = synchronizer
        
    async def dispatch(self, request: CommandRequest) -> CommandResult:
        """
        Dispatch a command to the appropriate entity.
        
        This method:
        1. Loads the target entity
        2. Executes the requested event method
        3. Coordinates persistence and real-time updates
        4. Returns the result
        """
        try:
            # Load entity
            entity = await self._load_entity(request)
            
            # Execute event
            result = await self._execute_event(entity, request)
            
            # Handle persistence and real-time
            await self._handle_post_execution(entity, request, result)
            
            return CommandResult(
                success=True,
                entity=entity,
                return_value=result.return_value,
                signals_updated=entity.get_updated_signals(),
                fragments_generated=result.fragments
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                error=str(e)
            )
    
    async def _load_entity(self, request: CommandRequest) -> Entity:
        """Load entity for command execution"""
        # Implementation depends on entity loading strategy
        pass
    
    async def _execute_event(self, entity: Entity, request: CommandRequest):
        """Execute the event method on the entity"""
        # Get event method
        event_method = entity.get_event_method(request.event_name)
        if not event_method:
            raise ValueError(f"Event {request.event_name} not found on {entity}")
        
        # Execute with parameters
        return await event_method(**request.parameters)
    
    async def _handle_post_execution(self, entity: Entity, request: CommandRequest, result):
        """Handle persistence and real-time updates after execution"""
        # Save entity changes
        await self.unit_of_work.register_entity(entity)
        
        # Synchronize real-time updates
        if entity.model_config.get("realtime", True):
            await self.synchronizer.sync_entity_update(entity, request.event_name)
        
        # Commit transaction
        await self.unit_of_work.commit()
```

### **2.3 Migrate Persistence System**

#### **Step 2.3.1: Move Persistence Backends**
```bash
mkdir -p framework/persistence/backends
cp src/starmodel/persistence/memory.py framework/persistence/backends/memory.py
cp src/starmodel/persistence/sql.py framework/persistence/backends/sql.py
```

```python
# framework/persistence/backends/__init__.py
"""
Persistence Backends - Pluggable Storage Systems

StarModel supports multiple persistence backends:
- Memory: Fast in-memory storage for development and caching
- SQL: Traditional relational database storage
- Redis: High-performance key-value storage
- Client: Browser-based storage (localStorage, sessionStorage)
"""

from .memory import MemoryBackend
from .sql import SQLBackend
from .base import PersistenceBackend

# Registry of available backends
AVAILABLE_BACKENDS = {
    "memory": MemoryBackend,
    "sql": SQLBackend,
    # "redis": RedisBackend,  # Future
    # "client": ClientBackend,  # Future
}

def get_backend(backend_type: str, **config) -> PersistenceBackend:
    """Get a configured backend instance"""
    if backend_type not in AVAILABLE_BACKENDS:
        raise ValueError(f"Unknown backend type: {backend_type}")
    
    backend_class = AVAILABLE_BACKENDS[backend_type]
    return backend_class(**config)

__all__ = [
    "MemoryBackend", "SQLBackend", "PersistenceBackend",
    "AVAILABLE_BACKENDS", "get_backend"
]
```

---

## Phase 3: Infrastructure Migration

### **3.1 Migrate Web Infrastructure**

#### **Step 3.1.1: Move FastHTML Adapter**
```bash
mkdir -p framework/infrastructure/web
cp src/starmodel/adapters/fasthtml.py framework/infrastructure/web/fasthtml_adapter.py
```

```python
# framework/infrastructure/web/fasthtml_adapter.py
"""
FastHTML Web Framework Adapter

This adapter integrates StarModel entities and events with the FastHTML
web framework, providing:
- Automatic route registration for @event methods
- Request/response handling
- Integration with Datastar for real-time updates
"""
from typing import Any, Dict, Optional
from fasthtml.common import FastHTML, Request, Response

from ...events.dispatching.dispatcher import EventDispatcher, CommandRequest
from ...entities.lifecycle.entity import Entity
from ..realtime.protocols.sse import SSEProtocol

class FastHTMLAdapter:
    """
    FastHTML integration adapter for StarModel.
    
    This adapter bridges StarModel's entity-event system with
    FastHTML's web framework capabilities.
    """
    
    def __init__(self, app: FastHTML, dispatcher: EventDispatcher):
        self.app = app
        self.dispatcher = dispatcher
        self.sse_protocol = SSEProtocol()
        
    def register_entity(self, entity_class: Type[Entity]):
        """Register all events from an entity class as HTTP routes"""
        entity_name = entity_class.__name__.lower()
        events = entity_class.get_events()
        
        for event_name, event_metadata in events.items():
            route_path = f"/{entity_name}/{event_name}"
            
            # Create route handler
            handler = self._create_event_handler(entity_class, event_name)
            
            # Register with FastHTML
            self.app.route(route_path, methods=[event_metadata.http_method])(handler)
            
    def _create_event_handler(self, entity_class: Type[Entity], event_name: str):
        """Create a FastHTML route handler for an entity event"""
        async def handler(request: Request):
            # Extract command request from HTTP request
            command_request = await self._extract_command_request(
                request, entity_class, event_name
            )
            
            # Dispatch command
            result = await self.dispatcher.dispatch(command_request)
            
            # Format response based on request type
            return await self._format_response(result, request)
        
        return handler
    
    async def _extract_command_request(self, request: Request, 
                                     entity_class: Type[Entity], 
                                     event_name: str) -> CommandRequest:
        """Extract StarModel command from FastHTML request"""
        # Implementation for parameter extraction
        pass
    
    async def _format_response(self, result, request: Request):
        """Format command result as appropriate HTTP response"""
        if self._is_sse_request(request):
            return await self.sse_protocol.create_sse_response(result)
        else:
            return self._create_json_response(result)
```

### **3.2 Migrate Real-time Infrastructure**

#### **Step 3.2.1: Create Real-time Protocols**
```python
# framework/realtime/protocols/sse.py
"""
Server-Sent Events Protocol Implementation

Handles real-time updates via SSE (Server-Sent Events) for browser clients.
"""
from typing import Any, Dict, AsyncGenerator
from fasthtml.common import StreamingResponse
import json

class SSEProtocol:
    """Server-Sent Events protocol for real-time updates"""
    
    async def create_sse_response(self, command_result) -> StreamingResponse:
        """Create SSE streaming response from command result"""
        async def event_stream():
            # Send signals update
            if command_result.signals_updated:
                yield self._format_signals_event(command_result.signals_updated)
            
            # Send fragments
            for fragment in command_result.fragments_generated or []:
                yield self._format_fragment_event(fragment)
                
            # End stream
            yield "event: complete\ndata: {}\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    def _format_signals_event(self, signals: Dict[str, Any]) -> str:
        """Format signals update as SSE event"""
        data = json.dumps({"signals": signals})
        return f"event: signals\ndata: {data}\n\n"
    
    def _format_fragment_event(self, fragment: Any) -> str:
        """Format HTML fragment as SSE event"""
        # Convert fragment to HTML string
        html = str(fragment) if fragment else ""
        data = json.dumps({"fragment": html})
        return f"event: fragment\ndata: {data}\n\n"
```

---

## Phase 4: Demo Apps Reorganization

### **4.1 Create Dedicated Demo Apps**

#### **Step 4.1.1: Counter App**
```bash
mkdir -p examples/counter-app/{entities,pages}
```

```python
# examples/counter-app/entities/counter.py
"""
Counter Entity - Simple Interactive Counter

This demonstrates StarModel's core capabilities:
- Entity with state (count)
- Interactive events (increment, decrement, reset)
- Real-time UI updates
- Persistent state
"""
from starmodel.entities import Entity, event

class Counter(Entity):
    """A simple counter that demonstrates entity-event patterns"""
    
    count: int = 0
    increment_count: int = 0
    
    model_config = {
        "store": "memory",  # Use memory backend for demo
        "realtime": True,   # Enable real-time updates
    }
    
    @event(description="Increase counter by specified amount")
    async def increment(self, amount: int = 1):
        """Increment the counter"""
        self.count += amount
        self.increment_count += 1
    
    @event(description="Decrease counter by specified amount")
    async def decrement(self, amount: int = 1):
        """Decrement the counter"""
        self.count -= amount
    
    @event(description="Reset counter to zero")
    async def reset(self):
        """Reset counter to zero"""
        self.count = 0
```

```python
# examples/counter-app/pages/counter_page.py
"""
Counter Page - UI for Counter Entity

Demonstrates:
- Entity-UI binding via signals
- Event-triggered interactions
- Real-time updates
"""
from fasthtml.common import *
from ..entities.counter import Counter

def counter_page():
    """Counter demonstration page"""
    return Div(
        H1("StarModel Counter Demo"),
        P("This counter demonstrates entity-driven interactions with real-time updates."),
        
        # Counter display - bound to entity signals
        Div(
            H2("Count: ", Span("0", data_text=Counter.count_signal)),
            P("Increments: ", Span("0", data_text=Counter.increment_count_signal)),
            cls="counter-display"
        ),
        
        # Interactive controls - bound to entity events
        Div(
            Button("+1", data_on_click=Counter.increment(1)),
            Button("+5", data_on_click=Counter.increment(5)),
            Button("-1", data_on_click=Counter.decrement(1)),
            Button("Reset", data_on_click=Counter.reset()),
            cls="counter-controls"
        ),
        
        # Real-time status
        P("Updates happen in real-time across all connected clients!"),
        
        cls="counter-app"
    )
```

```python
# examples/counter-app/main.py
"""
Counter App - Minimal StarModel Application

This is a complete, minimal StarModel application that demonstrates:
- Entity definition and behavior
- Automatic web UI generation
- Real-time interactions
- Zero configuration setup
"""
from fasthtml.common import FastHTML, serve
from starmodel import configure_starmodel
from .entities.counter import Counter
from .pages.counter_page import counter_page

# Create FastHTML app
app = FastHTML()

# Configure StarModel with the app
configure_starmodel(app, entities=[Counter])

# Add page route
@app.route("/")
def home():
    return counter_page()

if __name__ == "__main__":
    serve(app, host="localhost", port=8000)
```

#### **Step 4.1.2: Dashboard App**
```python
# examples/dashboard-app/entities/dashboard.py
"""
Dashboard Entity - Complex Interactive Dashboard

Demonstrates advanced StarModel capabilities:
- Complex entity state
- Multiple event types
- Computed properties
- Real-time data updates
"""
from starmodel.entities import Entity, event
from typing import Dict, List
from datetime import datetime

class Dashboard(Entity):
    """Interactive dashboard with metrics and controls"""
    
    metrics: Dict[str, float] = {}
    alerts: List[str] = []
    last_updated: datetime = None
    refresh_count: int = 0
    
    model_config = {
        "store": "memory",
        "realtime": True,
        "collaborative": True,  # Multiple users can interact
    }
    
    @event(description="Refresh dashboard metrics")
    async def refresh_metrics(self):
        """Refresh all dashboard metrics"""
        import random
        self.metrics = {
            "cpu_usage": random.uniform(10, 90),
            "memory_usage": random.uniform(20, 80),
            "disk_usage": random.uniform(15, 95),
            "network_io": random.uniform(0, 100),
        }
        self.last_updated = datetime.now()
        self.refresh_count += 1
    
    @event(description="Add a new alert")
    async def add_alert(self, message: str):
        """Add an alert to the dashboard"""
        self.alerts.append(f"{datetime.now().strftime('%H:%M:%S')}: {message}")
        if len(self.alerts) > 10:  # Keep only last 10 alerts
            self.alerts = self.alerts[-10:]
    
    @event(description="Clear all alerts")
    async def clear_alerts(self):
        """Clear all alerts"""
        self.alerts = []
    
    @property
    def average_metric(self) -> float:
        """Computed property: average of all metrics"""
        if not self.metrics:
            return 0.0
        return sum(self.metrics.values()) / len(self.metrics)
```

### **4.2 Update Full Demo**
```bash
# Move existing demo to full-demo
cp -r app/* examples/full-demo/
```

```python
# examples/full-demo/main.py
"""
Full StarModel Demo - Complete Feature Showcase

This comprehensive demo showcases all StarModel capabilities:
- Multiple entity types
- Complex interactions
- Real-time collaboration
- Multiple persistence backends
- Rich UI components
"""
from fasthtml.common import FastHTML, serve
from starmodel import configure_starmodel

# Import all demo entities
from .entities.counter import Counter
from .entities.dashboard import Dashboard
from .entities.chat import ChatRoom
from .entities.todo import TodoList
from .entities.user import User

# Import all demo pages
from .pages import *

app = FastHTML()

# Configure StarModel with all entities
configure_starmodel(app, entities=[
    Counter, Dashboard, ChatRoom, TodoList, User
])

# Register all demo routes
register_demo_routes(app)

if __name__ == "__main__":
    serve(app, host="localhost", port=8000)
```

---

## Phase 5: Import Path Updates & Cleanup

### **5.1 Update All Import Statements**

#### **Step 5.1.1: Create Import Migration Script**
```python
# tools/migration/update_imports.py
"""
Automated import path migration script

Updates all import statements from old framework-centric paths
to new domain-centric screaming architecture paths.
"""
import os
import re
from pathlib import Path
from typing import Dict, List

class ImportMigrator:
    """Handles automated import path updates"""
    
    def __init__(self):
        self.import_mappings = {
            # Core entity system
            "from starmodel.core.entity": "from starmodel.entities.lifecycle",
            "from starmodel.core.events": "from starmodel.events.commands", 
            "from starmodel.core.signals": "from starmodel.reactivity.signals",
            
            # Application layer
            "from starmodel.app.dispatcher": "from starmodel.events.dispatching",
            "from starmodel.app.bus": "from starmodel.events.streaming",
            "from starmodel.app.uow": "from starmodel.persistence.transactions",
            
            # Persistence layer
            "from starmodel.persistence.memory": "from starmodel.persistence.backends",
            "from starmodel.persistence.sql": "from starmodel.persistence.backends",
            "from starmodel.persistence.base": "from starmodel.persistence.repositories",
            
            # Web infrastructure
            "from starmodel.adapters.fasthtml": "from starmodel.infrastructure.web",
            "from starmodel.web": "from starmodel.infrastructure.web",
            
            # Specific class imports
            "import Entity": "from starmodel.entities import Entity",
            "import event": "from starmodel.events import event",
        }
        
    def migrate_file(self, file_path: Path):
        """Migrate import statements in a single file"""
        content = file_path.read_text()
        original_content = content
        
        # Apply all import mappings
        for old_import, new_import in self.import_mappings.items():
            content = re.sub(re.escape(old_import), new_import, content)
        
        # Write back if changed
        if content != original_content:
            file_path.write_text(content)
            print(f"Updated imports in: {file_path}")
            
    def migrate_directory(self, directory: Path):
        """Migrate all Python files in directory"""
        for py_file in directory.rglob("*.py"):
            self.migrate_file(py_file)

# Usage
if __name__ == "__main__":
    migrator = ImportMigrator()
    
    # Migrate framework code
    migrator.migrate_directory(Path("framework"))
    
    # Migrate examples
    migrator.migrate_directory(Path("examples"))
    
    print("Import migration completed!")
```

### **5.2 Update Package Configuration**

#### **Step 5.2.1: Update pyproject.toml**
```toml
# pyproject.toml
[project]
name = "starmodel"
version = "0.2.0"
description = "Entity-centric Python web framework for real-time collaborative applications"

[project.entry-points."starmodel.examples"]
counter = "examples.counter_app.main:app"
dashboard = "examples.dashboard_app.main:app"
collaboration = "examples.collaboration_app.main:app"
full_demo = "examples.full_demo.main:app"

[tool.setuptools.packages.find]
where = ["framework"]
include = ["starmodel*"]

[tool.setuptools.package-dir]
starmodel = "framework"
```

#### **Step 5.2.2: Create New Main Package**
```python
# framework/__init__.py
"""
StarModel - Entity-Centric Web Framework

StarModel enables developers to create real-time, collaborative web applications
by focusing on entities with behavior rather than technical infrastructure.

Key Concepts:
- Entities: Domain objects with both data and behavior (@event methods)
- Events: Interactive commands that users can trigger
- Real-time: Automatic synchronization across all connected clients
- Persistence: Pluggable backends (memory, SQL, Redis, client-side)
- Collaboration: Multi-user interactions with conflict resolution

Quick Start:
    from starmodel import Entity, event
    
    class Counter(Entity):
        count: int = 0
        
        @event
        async def increment(self):
            self.count += 1
"""

# Primary API - what developers interact with
from .entities import Entity
from .events import event
from .persistence import configure_persistence
from .infrastructure.web import configure_web
from .realtime import configure_realtime

# Configuration helper
def configure_starmodel(app, entities=None, **config):
    """
    Configure StarModel with a web application.
    
    Args:
        app: Web framework application (FastHTML, FastAPI, etc.)
        entities: List of entity classes to register
        **config: Additional configuration options
    """
    from .infrastructure.web.auto_adapter import detect_and_configure
    
    # Auto-detect web framework and configure
    detect_and_configure(app, entities or [], **config)

__version__ = "0.2.0"
__all__ = [
    "Entity", "event", "configure_starmodel",
    "configure_persistence", "configure_web", "configure_realtime"
]
```

### **5.3 Clean Up Old Structure**

#### **Step 5.3.1: Create Cleanup Script**
```python
# tools/migration/cleanup.py
"""
Clean up old framework-centric structure after migration is complete
"""
import shutil
from pathlib import Path

def cleanup_old_structure():
    """Remove old directories after successful migration"""
    old_paths = [
        "src/starmodel/core",
        "src/starmodel/app", 
        "src/starmodel/persistence",
        "src/starmodel/adapters",
        "src/starmodel/web",
        "app/entities",  # Moved to examples
        "app/pages",     # Moved to examples
    ]
    
    for path in old_paths:
        path_obj = Path(path)
        if path_obj.exists():
            if path_obj.is_dir():
                shutil.rmtree(path_obj)
                print(f"Removed directory: {path}")
            else:
                path_obj.unlink()
                print(f"Removed file: {path}")

if __name__ == "__main__":
    response = input("Are you sure you want to cleanup old structure? (yes/no): ")
    if response.lower() == "yes":
        cleanup_old_structure()
        print("Cleanup completed!")
    else:
        print("Cleanup cancelled.")
```

---

## Migration Validation

### **Validation Checklist**

#### **Phase 1 Validation**
- [ ] New directory structure created
- [ ] Compatibility layer established
- [ ] Migration tracker implemented
- [ ] All tests still pass

#### **Phase 2 Validation**
- [ ] Core entity system migrated
- [ ] Event system migrated
- [ ] Persistence system migrated
- [ ] All functionality preserved
- [ ] Import paths work for both old and new

#### **Phase 3 Validation**
- [ ] Web infrastructure migrated
- [ ] Real-time protocols migrated
- [ ] FastHTML adapter works
- [ ] SSE functionality preserved

#### **Phase 4 Validation**
- [ ] Demo apps reorganized
- [ ] Counter app works independently
- [ ] Dashboard app works independently
- [ ] Full demo works with all features

#### **Phase 5 Validation**
- [ ] All import paths updated
- [ ] Package configuration updated
- [ ] Old structure cleaned up
- [ ] New structure fully functional
- [ ] Documentation updated

### **Testing Strategy**

```python
# tests/migration/test_migration.py
"""Test suite to validate migration completeness"""
import pytest
from pathlib import Path

def test_all_files_migrated():
    """Ensure all files have been migrated"""
    from tools.migration.tracker import MigrationTracker
    
    tracker = MigrationTracker()
    status = tracker.get_migration_status()
    
    assert status["migrated"] == status["total_files"]
    assert status["remaining"] == 0

def test_new_import_paths_work():
    """Test that new import paths work correctly"""
    # Test core imports
    from starmodel.entities import Entity, event
    from starmodel.events.dispatching import EventDispatcher
    from starmodel.persistence.backends import MemoryBackend
    
    # Test that classes are properly imported
    assert Entity is not None
    assert event is not None
    assert EventDispatcher is not None
    assert MemoryBackend is not None

def test_backward_compatibility():
    """Test that old import paths still work during migration"""
    # These should work during migration period
    try:
        from starmodel.core.entity import Entity as OldEntity
        from starmodel.core.events import event as old_event
        assert OldEntity is not None
        assert old_event is not None
    except ImportError:
        pytest.skip("Backward compatibility imports removed")

def test_demo_apps_work():
    """Test that all demo apps can be imported and run"""
    from examples.counter_app.main import app as counter_app
    from examples.dashboard_app.main import app as dashboard_app
    from examples.full_demo.main import app as full_demo_app
    
    assert counter_app is not None
    assert dashboard_app is not None
    assert full_demo_app is not None
```

## Benefits After Migration

### **Developer Experience**
- **Intuitive Structure**: New developers immediately understand StarModel's purpose
- **Domain-Focused**: Code organization reflects business concepts, not technical layers
- **Easier Navigation**: Related functionality is grouped by purpose
- **Self-Documenting**: Directory names explain what each part does

### **Maintainability**
- **Clear Boundaries**: Each domain area has clear responsibilities
- **Reduced Coupling**: Infrastructure concerns are properly separated
- **Easier Testing**: Domain logic can be tested independently
- **Plugin Architecture**: New capabilities can be added without affecting core

### **Extensibility**
- **Plugin Points**: Clear extension points for new backends, protocols, etc.
- **Framework Agnostic**: Core domain logic independent of web framework
- **Multiple Apps**: Framework supports multiple application types
- **Deployment Flexibility**: Different deployment strategies for different needs

This migration transforms StarModel from a generic framework into a **self-documenting, domain-driven platform** that screams its purpose: **"Entity-centric, event-driven, real-time collaborative applications."**