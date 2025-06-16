"""
Application Service Layer

This module implements the APPLICATION SERVICE LAYER from clean architecture,
providing the bridge between presentation (FastHTML routes) and domain (entities).

Key components:
- dispatcher: Request → Event binding and command execution  
- uow: Unit-of-Work pattern for transactions and domain events
- bus: EventBus interface for SSE, WebSocket, and multi-instance coordination
"""

from .dispatcher import call_event
from .uow import UnitOfWork
from .bus import InProcessBus

__all__ = [
    'call_event',
    'UnitOfWork', 
    'InProcessBus',
]