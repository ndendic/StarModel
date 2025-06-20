"""
Persistence Repositories - Data Access Layer

💾 Clean Data Access Patterns:
This module provides the repository pattern implementation for StarModel,
defining clean interfaces for data access and supporting multiple
persistence backends through unified abstractions.

Components:
- EntityRepository: Standard interface for all persistence backends
- PersistenceManager: Factory and coordinator for backends
- Repository patterns and base classes
- Query abstractions and filtering
"""

from .interface import (
    EntityRepository, QueryFilter, QueryResult, QueryOptions,
    QueryOperator, SortDirection, TransactionContext, QueryBuilder
)
from .manager import (
    PersistenceManager, BackendRegistry, BackendConfig,
    PersistenceError, BackendNotFoundError, BackendInitializationError
)
from .base import (
    BaseRepository, RepositoryError, EntityNotFoundError,
    TransactionError, ValidationError, RepositoryMetrics
)

__all__ = [
    # Interface components
    "EntityRepository", "QueryFilter", "QueryResult", "QueryOptions",
    "QueryOperator", "SortDirection", "TransactionContext", "QueryBuilder",
    
    # Manager components
    "PersistenceManager", "BackendRegistry", "BackendConfig",
    "PersistenceError", "BackendNotFoundError", "BackendInitializationError",
    
    # Base components
    "BaseRepository", "RepositoryError", "EntityNotFoundError",
    "TransactionError", "ValidationError", "RepositoryMetrics"
]