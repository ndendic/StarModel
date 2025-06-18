"""
StarModel Persistence Module

Infrastructure adapters for different storage backends.
Implements the persistence ports defined in the core domain.
"""

from .base import EntityPersistenceBackend
from .memory import MemoryRepo, get_memory_persistence

__all__ = [
    "EntityPersistenceBackend", 
    "MemoryRepo",
    "get_memory_persistence"
]