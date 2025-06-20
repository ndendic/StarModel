"""
StarModel Framework - Entity-Centric Web Framework

⭐ CLEAN ARCHITECTURE WITH SCREAMING ORGANIZATION ⭐

StarModel combines clean architecture principles with screaming architecture organization,
making both the purpose and structure immediately clear:

🎯 entities/      - THE HEART: Domain entities with behavior
🚀 events/        - EVENT-DRIVEN: Commands, dispatching, and streaming  
⚡ realtime/      - LIVE UPDATES: Synchronization and broadcasting
🔄 reactivity/    - REACTIVE UI: Signals, binding, and automatic updates
💾 persistence/   - DATA LAYER: Repositories, transactions, and backends
🔧 infrastructure/ - TECHNICAL: Web adapters, DI container, configuration

Phase 1 Application Service Layer: ✅ COMPLETED
- Event Dispatcher with clean architecture separation
- Unit of Work for transaction coordination  
- Event Bus for domain event publishing
- Dependency Injection container
- Configuration-driven service composition
- Web abstraction layer with FastHTML adapter

Quick Start:
    from starmodel import Entity, event, configure_starmodel
    
    class Counter(Entity):
        count: int = 0
        
        @event
        async def increment(self):
            self.count += 1
    
    # Configure with clean architecture
    container = await configure_starmodel(entities=[Counter])

The framework provides:
- Clean architecture with proper separation of concerns
- Automatic dependency injection and service composition
- Real-time state synchronization across clients
- Pluggable persistence backends (memory, SQL, Redis)
- Event-driven interactions with proper domain events
- Configuration-driven setup for different environments
"""

# Primary API - Clean Architecture Components
from .entities.lifecycle.entity import Entity, EntityStore
from .events.commands.event import event
from .infrastructure.deployment.configurator import configure_starmodel

# Configuration and environment management
from .infrastructure.dependency_injection.configuration import (
    ApplicationConfig, Environment, get_config, set_config
)

# Core clean architecture components (for advanced users)
from .events.dispatching.dispatcher import EventDispatcher
from .events.streaming.event_bus import EventBus, InProcessEventBus
from .persistence.transactions.unit_of_work import UnitOfWork
from .infrastructure.dependency_injection.container import DIContainer

# Backward compatibility during migration
try:
    from .entities.lifecycle.entity import Entity as CoreEntity
    from .events.commands.event import event as core_event
except ImportError:
    CoreEntity = Entity
    core_event = event

# Legacy aliases
def configure_app(*args, **kwargs):
    """Backward compatibility alias for configure_starmodel"""
    return configure_starmodel(*args, **kwargs)

def get_backend(backend_type: str, **config):
    """Get persistence backend - now handled by DI container"""
    # This is now handled by the persistence manager in the DI container
    container = get_current_container()
    if container:
        persistence_manager = container.get("PersistenceManager")
        return persistence_manager.get_backend_by_type(backend_type)
    return None

def configure_web(app, **config):
    """Web configuration - now part of configure_starmodel"""
    pass

# Version and status
__version__ = "0.2.0-clean-architecture"

# Primary exports - what developers use
__all__ = [
    # 🎯 Core Domain API
    "Entity", "EntityStore", "event",
    
    # 🚀 Application Configuration  
    "configure_starmodel", "ApplicationConfig", "Environment",
    "get_config", "set_config",
    
    # 🔧 Advanced Clean Architecture Components
    "EventDispatcher", "EventBus", "InProcessEventBus", 
    "UnitOfWork", "DIContainer",
    
    # 🔄 Backward Compatibility
    "CoreEntity", "core_event", "configure_app", 
    "get_backend", "configure_web"
]

# Import current container function
try:
    from .infrastructure.dependency_injection.container import get_current_container
except ImportError:
    def get_current_container():
        return None

# Development status indicator  
print("🚀 StarModel Framework - Clean Architecture Edition")
print("   ✅ Phase 1 Application Service Layer: COMPLETED")
print("   🎯 Entity-centric domain design")
print("   🔧 Dependency injection and configuration")
print("   💾 Repository pattern and Unit of Work")
print("   🚀 Event-driven architecture with domain events")
print("   ⚡ Real-time synchronization ready")
print("   🔄 Ready for Phase 2: Enhanced persistence backends")
print("")
print("📖 Quick Start:")
print("   from starmodel import Entity, event, configure_starmodel")
print("   container = await configure_starmodel(entities=[YourEntity])")
print("")