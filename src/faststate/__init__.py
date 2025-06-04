"""
FastState - Reactive State Management for FastHTML

A powerful state management system that integrates with FastHTML's dependency injection
to provide automatic state management with scoping and real-time updates.
"""
from .state import State, event, datastar_script, DatastarPayload
from .state import rt as states_rt
from .registry import StateScope, StateConfig, StateRegistry, state_registry
# from .fasthtml_integration import (
#     initialize_faststate, create_state_middleware, get_state_info
# )
from .persistence import (
    StatePersistenceBackend, RedisStatePersistence, DatabaseStatePersistence, 
    MemoryStatePersistence, StatePersistenceManager, persistence_manager
)


__all__ = [
    # Core state components
    'State',
    'event',
    'datastar_script',
    'DatastarPayload',
    'states_rt',
    # Registry
    'StateScope',
    'StateConfig',
    'StateRegistry',
    'state_registry',
    
    # Persistence layer
    'StatePersistenceBackend',
    'RedisStatePersistence', 
    'DatabaseStatePersistence',
    'MemoryStatePersistence',
    'StatePersistenceManager',
    'persistence_manager',
]