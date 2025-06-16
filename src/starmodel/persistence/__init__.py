"""
StarModel Persistence Module

Infrastructure adapters for different storage backends.
Implements the persistence ports defined in the core domain.
"""

from .base import EntityPersistenceBackend, EntityStore
from .memory import MemoryEntityPersistence, memory_persistence

__all__ = [
    "EntityPersistenceBackend", 
    "EntityStore", 
    "MemoryEntityPersistence", 
    "memory_persistence"
]