"""
FastState - Reactive State Management for FastHTML

A powerful state management system that integrates with FastHTML's dependency injection
to provide automatic state management with scoping, authentication, and real-time updates.
"""

from .state import ReactiveState, event, _get_state
from .registry import StateScope, StateConfig, FastStateRegistry, state_registry

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
]

def hello() -> str:
    return "Hello from faststate!"
