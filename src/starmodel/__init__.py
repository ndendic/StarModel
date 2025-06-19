"""
StarModel - Reactive Entity Management for FastHTML

A powerful entity management system that integrates with FastHTML's dependency injection
to provide automatic entity management with scoping and real-time updates.
"""

# Import from new organized modules while maintaining backward compatibility
from .core import Entity, SQLEntity, event, datastar_script, DatastarPayload, rt as entities_rt
from .persistence import (
    EntityPersistenceBackend, 
    MemoryRepo, get_memory_persistence,
    SQLModelBackend,
    start_all_cleanup, stop_all_cleanup, configure_all_cleanup
)

# Import new application service layer components
from .app import call_event, UnitOfWork, InProcessBus
from .app.configurator import configure_app, validate_app_configuration
from .adapters.fasthtml import include_entity, register_entities, register_all_entities

__all__ = [
    # Core entity components
    'Entity',
    'SQLEntity',
    'event',
    'datastar_script',
    'DatastarPayload',
    'entities_rt',
    
    # Application service layer
    'call_event',
    'UnitOfWork',
    'InProcessBus',
    'configure_app',
    'validate_app_configuration',
    
    # Adapters
    'include_entity',
    'register_entities',
    'register_all_entities',
    # Persistence layer
    'EntityPersistenceBackend',
    'MemoryRepo',
    'get_memory_persistence',
    'SQLModelBackend',
    'start_all_cleanup',
    'stop_all_cleanup', 
    'configure_all_cleanup',
]