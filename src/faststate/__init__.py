"""
FastState - Reactive State Management for FastHTML

A powerful state management system that integrates with FastHTML's dependency injection
to provide automatic state management with scoping and real-time updates.
"""

from .state import State, event, _get_state
from .registry import StateScope, StateConfig, FastStateRegistry, state_registry
# from .fasthtml_integration import (
#     initialize_faststate, create_state_middleware, get_state_info
# )
from .sse_manager import StateSSEManager, SSEConnection, sse_manager
from .persistence import (
    StatePersistenceBackend, RedisStatePersistence, DatabaseStatePersistence, 
    MemoryStatePersistence, StatePersistenceManager, persistence_manager
)

__all__ = [
    # Core state components
    'State',
    'event',
    '_get_state',
    
    # Registry system
    'StateScope',
    'StateConfig',
    'FastStateRegistry',
    'state_registry',
    
    # FastHTML integration
    # 'initialize_faststate',
    # 'create_state_middleware',
    # 'get_state_info',
    
    # SSE management
    'StateSSEManager',
    'SSEConnection',
    'sse_manager',
    
    # Persistence layer
    'StatePersistenceBackend',
    'RedisStatePersistence', 
    'DatabaseStatePersistence',
    'MemoryStatePersistence',
    'StatePersistenceManager',
    'persistence_manager',
]
