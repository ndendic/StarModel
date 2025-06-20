"""
Persistence Backends - Storage Implementation Layer

💾 Pluggable Storage Implementations:
This module provides concrete implementations of the EntityRepository interface
for different storage backends, enabling flexible persistence strategies.

Available Backends:
- MemoryRepository: In-memory storage with TTL and cleanup
- Client storage repositories (planned)
- SQL repositories (planned)
- Redis repositories (planned)
"""

from .memory import MemoryRepository, EntityRecord, MemoryTransaction

__all__ = [
    "MemoryRepository", "EntityRecord", "MemoryTransaction"
]