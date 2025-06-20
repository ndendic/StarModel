"""
Persistence Repository Interface

💾 Standard Data Access Contract:
This module defines the standard interface that all persistence backends
must implement, ensuring consistent data access patterns across different
storage systems while maintaining clean architecture principles.
"""

from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Type, Union, Generic, TypeVar,
    AsyncIterator, Callable
)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Forward reference to Entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...entities.lifecycle.entity import Entity

EntityType = TypeVar('EntityType', bound='Entity')

class QueryOperator(Enum):
    """Query operators for filtering"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"

class SortDirection(Enum):
    """Sort direction for ordering"""
    ASC = "asc"
    DESC = "desc"

@dataclass
class QueryFilter:
    """Represents a single filter condition"""
    field: str
    operator: QueryOperator
    value: Any = None
    
    def __post_init__(self):
        """Validate filter after creation"""
        if self.operator in (QueryOperator.IS_NULL, QueryOperator.IS_NOT_NULL):
            # These operators don't need a value
            self.value = None
        elif self.value is None and self.operator not in (QueryOperator.IS_NULL, QueryOperator.IS_NOT_NULL):
            raise ValueError(f"Value required for operator {self.operator}")

@dataclass
class SortCriteria:
    """Represents sorting criteria"""
    field: str
    direction: SortDirection = SortDirection.ASC

@dataclass
class QueryOptions:
    """Options for querying entities"""
    filters: List[QueryFilter] = field(default_factory=list)
    sort_by: List[SortCriteria] = field(default_factory=list)
    limit: Optional[int] = None
    offset: int = 0
    include_count: bool = False
    
    def add_filter(self, field: str, operator: QueryOperator, value: Any = None) -> 'QueryOptions':
        """Add a filter condition"""
        self.filters.append(QueryFilter(field, operator, value))
        return self
    
    def add_sort(self, field: str, direction: SortDirection = SortDirection.ASC) -> 'QueryOptions':
        """Add sorting criteria"""
        self.sort_by.append(SortCriteria(field, direction))
        return self
    
    def equals(self, field: str, value: Any) -> 'QueryOptions':
        """Convenience method for equality filter"""
        return self.add_filter(field, QueryOperator.EQUALS, value)
    
    def greater_than(self, field: str, value: Any) -> 'QueryOptions':
        """Convenience method for greater than filter"""
        return self.add_filter(field, QueryOperator.GREATER_THAN, value)
    
    def contains(self, field: str, value: str) -> 'QueryOptions':
        """Convenience method for contains filter"""
        return self.add_filter(field, QueryOperator.CONTAINS, value)
    
    def sort_asc(self, field: str) -> 'QueryOptions':
        """Convenience method for ascending sort"""
        return self.add_sort(field, SortDirection.ASC)
    
    def sort_desc(self, field: str) -> 'QueryOptions':
        """Convenience method for descending sort"""
        return self.add_sort(field, SortDirection.DESC)

@dataclass
class QueryResult(Generic[EntityType]):
    """Result of a query operation"""
    entities: List[EntityType]
    total_count: Optional[int] = None
    has_more: bool = False
    query_time_ms: Optional[float] = None
    
    def __len__(self) -> int:
        return len(self.entities)
    
    def __iter__(self):
        return iter(self.entities)
    
    def __getitem__(self, index):
        return self.entities[index]
    
    def first(self) -> Optional[EntityType]:
        """Get first entity or None"""
        return self.entities[0] if self.entities else None
    
    def last(self) -> Optional[EntityType]:
        """Get last entity or None"""
        return self.entities[-1] if self.entities else None

class TransactionContext:
    """Context for database transactions"""
    
    def __init__(self, transaction_id: str, isolation_level: str = "READ_COMMITTED"):
        self.transaction_id = transaction_id
        self.isolation_level = isolation_level
        self.is_active = False
        self.is_committed = False
        self.is_rolled_back = False
        self.started_at: Optional[datetime] = None
        self.committed_at: Optional[datetime] = None

class EntityRepository(ABC, Generic[EntityType]):
    """
    Abstract repository interface for entity persistence.
    
    This interface defines the contract that all persistence backends
    must implement, ensuring consistent data access patterns while
    allowing for backend-specific optimizations.
    """
    
    @abstractmethod
    async def save(self, entity: EntityType, context: Optional[TransactionContext] = None) -> str:
        """
        Save an entity to the repository.
        
        Args:
            entity: The entity to save
            context: Optional transaction context
            
        Returns:
            The entity ID
        """
        pass
    
    @abstractmethod
    async def load(self, entity_class: Type[EntityType], entity_id: str, 
                   context: Optional[TransactionContext] = None) -> Optional[EntityType]:
        """
        Load an entity by ID.
        
        Args:
            entity_class: The entity class type
            entity_id: The entity ID to load
            context: Optional transaction context
            
        Returns:
            The entity instance or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_class: Type[EntityType], entity_id: str,
                     context: Optional[TransactionContext] = None) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            entity_class: The entity class type
            entity_id: The entity ID to delete
            context: Optional transaction context
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, entity_class: Type[EntityType], entity_id: str,
                     context: Optional[TransactionContext] = None) -> bool:
        """
        Check if an entity exists.
        
        Args:
            entity_class: The entity class type
            entity_id: The entity ID to check
            context: Optional transaction context
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def query(self, entity_class: Type[EntityType], options: QueryOptions,
                    context: Optional[TransactionContext] = None) -> QueryResult[EntityType]:
        """
        Query entities with filtering and sorting.
        
        Args:
            entity_class: The entity class type
            options: Query options (filters, sorting, pagination)
            context: Optional transaction context
            
        Returns:
            Query result with entities and metadata
        """
        pass
    
    @abstractmethod
    async def count(self, entity_class: Type[EntityType], filters: Optional[List[QueryFilter]] = None,
                    context: Optional[TransactionContext] = None) -> int:
        """
        Count entities matching filters.
        
        Args:
            entity_class: The entity class type
            filters: Optional list of filters
            context: Optional transaction context
            
        Returns:
            Number of matching entities
        """
        pass
    
    # Batch operations
    @abstractmethod
    async def save_batch(self, entities: List[EntityType], 
                         context: Optional[TransactionContext] = None) -> List[str]:
        """
        Save multiple entities in a batch.
        
        Args:
            entities: List of entities to save
            context: Optional transaction context
            
        Returns:
            List of entity IDs
        """
        pass
    
    @abstractmethod
    async def load_batch(self, entity_class: Type[EntityType], entity_ids: List[str],
                         context: Optional[TransactionContext] = None) -> List[Optional[EntityType]]:
        """
        Load multiple entities by ID.
        
        Args:
            entity_class: The entity class type
            entity_ids: List of entity IDs to load
            context: Optional transaction context
            
        Returns:
            List of entity instances (None for not found)
        """
        pass
    
    @abstractmethod
    async def delete_batch(self, entity_class: Type[EntityType], entity_ids: List[str],
                           context: Optional[TransactionContext] = None) -> int:
        """
        Delete multiple entities by ID.
        
        Args:
            entity_class: The entity class type
            entity_ids: List of entity IDs to delete
            context: Optional transaction context
            
        Returns:
            Number of entities actually deleted
        """
        pass
    
    # Transaction support
    @abstractmethod
    async def begin_transaction(self, isolation_level: str = "READ_COMMITTED") -> TransactionContext:
        """
        Begin a new transaction.
        
        Args:
            isolation_level: Transaction isolation level
            
        Returns:
            Transaction context
        """
        pass
    
    @abstractmethod
    async def commit_transaction(self, context: TransactionContext):
        """
        Commit a transaction.
        
        Args:
            context: Transaction context to commit
        """
        pass
    
    @abstractmethod
    async def rollback_transaction(self, context: TransactionContext):
        """
        Rollback a transaction.
        
        Args:
            context: Transaction context to rollback
        """
        pass
    
    # Cleanup and maintenance
    @abstractmethod
    async def cleanup_expired(self, entity_class: Type[EntityType], 
                              before: datetime) -> int:
        """
        Clean up expired entities.
        
        Args:
            entity_class: The entity class type
            before: Remove entities older than this datetime
            
        Returns:
            Number of entities cleaned up
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get repository performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        pass
    
    # Stream operations for large datasets
    async def stream_all(self, entity_class: Type[EntityType], 
                         batch_size: int = 100,
                         context: Optional[TransactionContext] = None) -> AsyncIterator[EntityType]:
        """
        Stream all entities of a type.
        
        Args:
            entity_class: The entity class type
            batch_size: Number of entities to fetch per batch
            context: Optional transaction context
            
        Yields:
            Entity instances
        """
        offset = 0
        while True:
            options = QueryOptions(limit=batch_size, offset=offset)
            result = await self.query(entity_class, options, context)
            
            if not result.entities:
                break
            
            for entity in result.entities:
                yield entity
            
            if len(result.entities) < batch_size:
                break
            
            offset += batch_size
    
    async def stream_query(self, entity_class: Type[EntityType], options: QueryOptions,
                           batch_size: int = 100,
                           context: Optional[TransactionContext] = None) -> AsyncIterator[EntityType]:
        """
        Stream query results in batches.
        
        Args:
            entity_class: The entity class type
            options: Query options
            batch_size: Number of entities to fetch per batch
            context: Optional transaction context
            
        Yields:
            Entity instances
        """
        batch_options = QueryOptions(
            filters=options.filters,
            sort_by=options.sort_by,
            limit=batch_size,
            offset=options.offset
        )
        
        total_fetched = 0
        max_entities = options.limit or float('inf')
        
        while total_fetched < max_entities:
            result = await self.query(entity_class, batch_options, context)
            
            if not result.entities:
                break
            
            for entity in result.entities:
                if total_fetched >= max_entities:
                    break
                yield entity
                total_fetched += 1
            
            if len(result.entities) < batch_size:
                break
            
            batch_options.offset += batch_size

# Query builder helpers
class QueryBuilder:
    """Builder for constructing complex queries"""
    
    def __init__(self):
        self.options = QueryOptions()
    
    def where(self, field: str, operator: QueryOperator, value: Any = None) -> 'QueryBuilder':
        """Add a where condition"""
        self.options.add_filter(field, operator, value)
        return self
    
    def equals(self, field: str, value: Any) -> 'QueryBuilder':
        """Add equals condition"""
        return self.where(field, QueryOperator.EQUALS, value)
    
    def gt(self, field: str, value: Any) -> 'QueryBuilder':
        """Add greater than condition"""
        return self.where(field, QueryOperator.GREATER_THAN, value)
    
    def lt(self, field: str, value: Any) -> 'QueryBuilder':
        """Add less than condition"""
        return self.where(field, QueryOperator.LESS_THAN, value)
    
    def contains(self, field: str, value: str) -> 'QueryBuilder':
        """Add contains condition"""
        return self.where(field, QueryOperator.CONTAINS, value)
    
    def order_by(self, field: str, direction: SortDirection = SortDirection.ASC) -> 'QueryBuilder':
        """Add sorting"""
        self.options.add_sort(field, direction)
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """Set limit"""
        self.options.limit = count
        return self
    
    def offset(self, count: int) -> 'QueryBuilder':
        """Set offset"""
        self.options.offset = count
        return self
    
    def build(self) -> QueryOptions:
        """Build the final query options"""
        return self.options

# Convenience functions
def query() -> QueryBuilder:
    """Create a new query builder"""
    return QueryBuilder()

def equals(field: str, value: Any) -> QueryFilter:
    """Create an equals filter"""
    return QueryFilter(field, QueryOperator.EQUALS, value)

def greater_than(field: str, value: Any) -> QueryFilter:
    """Create a greater than filter"""
    return QueryFilter(field, QueryOperator.GREATER_THAN, value)

def contains(field: str, value: str) -> QueryFilter:
    """Create a contains filter"""
    return QueryFilter(field, QueryOperator.CONTAINS, value)

# Export main components
__all__ = [
    "EntityRepository", "QueryFilter", "QueryOptions", "QueryResult",
    "QueryOperator", "SortDirection", "SortCriteria", "TransactionContext",
    "QueryBuilder", "query", "equals", "greater_than", "contains"
]