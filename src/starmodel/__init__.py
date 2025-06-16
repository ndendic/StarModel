"""
StarModel - Reactive Entity Management for FastHTML

A powerful entity management system that integrates with FastHTML's dependency injection
to provide automatic entity management with scoping and real-time updates.
"""

# Import from new organized modules while maintaining backward compatibility
from .core import Entity, event, datastar_script, DatastarPayload, rt as entities_rt
from .persistence import (
    EntityStore, EntityPersistenceBackend, 
    MemoryEntityPersistence, memory_persistence
)

# Import new application service layer components
from .app import call_event, UnitOfWork, InProcessBus
from .adapters.persistence import persistence_manager
from .adapters.web_fasthtml import include_entity, register_entities, register_all_entities

__all__ = [
    # Core entity components
    'Entity',
    'event',
    'datastar_script',
    'DatastarPayload',
    'entities_rt',
    
    # Application service layer
    'call_event',
    'UnitOfWork',
    'InProcessBus',
    
    # Adapters
    'persistence_manager',
    'include_entity',
    'register_entities',
    'register_all_entities',
    # Persistence layer
    'EntityStore',
    'EntityPersistenceBackend',
    'MemoryEntityPersistence',
    'memory_persistence',
]