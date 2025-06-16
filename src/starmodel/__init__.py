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

__all__ = [
    # Core entity components
    'Entity',
    'event',
    'datastar_script',
    'DatastarPayload',
    'entities_rt',
    # Registry
    'EntityStore',
    
    # Persistence layer
    'EntityPersistenceBackend',
    'MemoryEntityPersistence',
    'memory_persistence',
]