"""
Persistence - Data Storage and Retrieval

💾 Pluggable Storage Backends:
Unified persistence layer that supports multiple storage backends.
Entities choose their storage through configuration, not inheritance.

Structure:
- backends/: Storage implementations (Memory, SQL, Redis, Client)
- repositories/: Data access patterns and interfaces
- transactions/: ACID operations and Unit of Work pattern
- caching/: Performance optimizations and caching strategies

Example:
    from starmodel.persistence import configure_backends
    
    # Configure multiple backends
    configure_backends({
        "memory": {"cleanup_interval": 300},
        "sql": {"url": "sqlite:///app.db"},
        "redis": {"url": "redis://localhost:6379"}
    })
    
    class User(Entity):
        name: str
        email: str
        
        model_config = {
            "store": "sql",  # Uses SQL backend
            "cache": "redis"  # With Redis caching
        }
"""

# Primary exports
try:
    from .backends import get_backend, configure_backends, MemoryBackend, SQLBackend
    from .repositories.base import Repository, EntityRepository
    from .transactions.unit_of_work import UnitOfWork
    from .caching.cache_manager import CacheManager
except ImportError:
    # Placeholders during migration
    get_backend = None
    configure_backends = None
    MemoryBackend = None
    SQLBackend = None
    Repository = None
    EntityRepository = None
    UnitOfWork = None
    CacheManager = None

def configure_persistence(**config):
    """Configure persistence layer"""
    # Placeholder implementation
    pass

__all__ = [
    "get_backend", "configure_backends", "MemoryBackend", "SQLBackend",
    "Repository", "EntityRepository", "UnitOfWork", "CacheManager",
    "configure_persistence"
]