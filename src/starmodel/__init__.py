"""
StarModel - Reactive State Management for FastHTML

A powerful state management system that integrates with FastHTML's dependency injection
to provide automatic state management with scoping and real-time updates.
"""
from .state import State, datastar_script
from .event import event, DatastarPayload
from .event import rt as states_rt
from .persistence import (
    StateStore, StatePersistenceBackend, # RedisStatePersistence, DatabaseStatePersistence, 
    MemoryStatePersistence, memory_persistence
)


__all__ = [
    # Core state components
    'State',
    'event',
    'datastar_script',
    'DatastarPayload',
    'states_rt',
    # Registry
    'StateStore',
    
    # Persistence layer
    'StatePersistenceBackend',
    # 'RedisStatePersistence', 
    # 'DatabaseStatePersistence',
    'MemoryStatePersistence',
    'memory_persistence',
]