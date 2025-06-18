"""
StarModel Persistence Module

Infrastructure adapters for different storage backends.
Implements the persistence ports defined in the core domain.
"""

from typing import List
from .base import EntityPersistenceBackend
from .memory import MemoryRepo, get_memory_persistence
from .datastar import DatastarRepo

# Global registry of active persistence backends for cleanup management
_active_backends: List[EntityPersistenceBackend] = []

def register_backend(backend: EntityPersistenceBackend) -> None:
    """Register a persistence backend for global cleanup management."""
    if backend not in _active_backends:
        _active_backends.append(backend)

def start_all_cleanup() -> None:
    """Start cleanup tasks for all registered backends."""
    for backend in _active_backends:
        backend.start_cleanup()

def stop_all_cleanup() -> None:
    """Stop cleanup tasks for all registered backends."""
    for backend in _active_backends:
        backend.stop_cleanup()

def configure_all_cleanup(enabled: bool = True, interval: int = 300) -> None:
    """Configure cleanup for all registered backends."""
    for backend in _active_backends:
        backend.configure_cleanup(enabled, interval)

__all__ = [
    "EntityPersistenceBackend", 
    "MemoryRepo",
    "get_memory_persistence",
    "DatastarRepo",
    "register_backend",
    "start_all_cleanup", 
    "stop_all_cleanup",
    "configure_all_cleanup"
]