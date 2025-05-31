"""
FastState - Reactive State Management for FastHTML

A powerful state management system that integrates with FastHTML's dependency injection
to provide automatic state management with scoping and real-time updates.
"""

from .state import ReactiveState, event, _get_state
from .registry import StateScope, StateConfig, FastStateRegistry, state_registry
from .fasthtml_integration import (
    initialize_faststate, create_state_middleware, get_state_info
)

__all__ = [
    # Core state components
    'ReactiveState',
    'event',
    '_get_state',
    
    # Registry system
    'StateScope',
    'StateConfig', 
    'FastStateRegistry',
    'state_registry',
    
    # FastHTML integration
    'initialize_faststate',
    'create_state_middleware',
    'get_state_info',
]

def hello() -> str:
    return "Hello from faststate!"
