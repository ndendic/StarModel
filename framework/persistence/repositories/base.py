"""
Base Repository - Common Repository Functionality

🏗️ Shared Repository Foundation:
This module provides base classes and common functionality for all
persistence backend implementations, reducing code duplication and
ensuring consistent behavior across different storage systems.
"""

from abc import ABC
from typing import Type, Optional, List, Dict, Any, AsyncIterator
from datetime import datetime, timedelta
import asyncio
import logging
import uuid
from dataclasses import dataclass

from .interface import (
    EntityRepository, QueryOptions, QueryResult, QueryFilter, 
    TransactionContext, EntityType
)

logger = logging.getLogger(__name__)

class RepositoryError(Exception):
    """Base exception for repository operations"""
    pass

class EntityNotFoundError(RepositoryError):
    """Raised when an entity is not found"""
    pass

class TransactionError(RepositoryError):
    """Raised when transaction operations fail"""
    pass

class ValidationError(RepositoryError):
    """Raised when entity validation fails"""
    pass

@dataclass
class RepositoryMetrics:
    """Metrics collected by repository implementations"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_response_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    entities_count: int = 0
    last_cleanup: Optional[datetime] = None
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations / max(self.total_operations, 1),
            "average_response_time_ms": self.average_response_time_ms,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
            "entities_count": self.entities_count,
            "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None,
            "uptime_seconds": self.uptime_seconds
        }

class BaseRepository(EntityRepository[EntityType], ABC):
    """
    Base repository implementation providing common functionality.
    
    This class provides:
    - Metrics collection
    - Error handling
    - Validation
    - Transaction context management
    - Logging and monitoring
    """
    
    def __init__(self, **config):
        self.config = config
        self.metrics = RepositoryMetrics()
        self.start_time = datetime.now()
        self._is_initialized = False
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    async def initialize(self):
        """Initialize the repository"""
        if self._is_initialized:
            return
        
        self._logger.info(f"Initializing {self.__class__.__name__}")
        await self._do_initialize()
        self._is_initialized = True
        self._logger.info(f"{self.__class__.__name__} initialized successfully")
    
    async def shutdown(self):
        """Shutdown the repository"""
        if not self._is_initialized:
            return
        
        self._logger.info(f"Shutting down {self.__class__.__name__}")
        await self._do_shutdown()
        self._is_initialized = False
        self._logger.info(f"{self.__class__.__name__} shutdown complete")
    
    async def _do_initialize(self):
        """Override in subclasses for specific initialization"""
        pass
    
    async def _do_shutdown(self):
        """Override in subclasses for specific shutdown"""
        pass
    
    # Metrics and monitoring
    async def get_metrics(self) -> Dict[str, Any]:
        """Get repository performance metrics"""
        self.metrics.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        return self.metrics.to_dict()
    
    def _record_operation_start(self) -> datetime:
        """Record the start of an operation"""
        return datetime.now()
    
    def _record_operation_success(self, start_time: datetime):
        """Record a successful operation"""
        duration = (datetime.now() - start_time).total_seconds() * 1000
        self.metrics.total_operations += 1
        self.metrics.successful_operations += 1
        
        # Update average response time
        total_time = self.metrics.average_response_time_ms * (self.metrics.successful_operations - 1)
        self.metrics.average_response_time_ms = (total_time + duration) / self.metrics.successful_operations
    
    def _record_operation_failure(self, start_time: datetime, error: Exception):
        """Record a failed operation"""
        self.metrics.total_operations += 1
        self.metrics.failed_operations += 1
        self._logger.error(f"Operation failed: {error}")
    
    def _record_cache_hit(self):
        """Record a cache hit"""
        self.metrics.cache_hits += 1
    
    def _record_cache_miss(self):
        """Record a cache miss"""
        self.metrics.cache_misses += 1
    
    # Validation helpers
    def _validate_entity(self, entity: EntityType):
        """Validate entity before persistence"""
        if not entity:
            raise ValidationError("Entity cannot be None")
        
        # Basic validation - subclasses can override
        if hasattr(entity, 'model_validate'):
            try:
                entity.model_validate(entity.model_dump())
            except Exception as e:
                raise ValidationError(f"Entity validation failed: {e}")
    
    def _validate_entity_id(self, entity_id: str):
        """Validate entity ID"""
        if not entity_id or not isinstance(entity_id, str):
            raise ValidationError("Entity ID must be a non-empty string")
    
    def _validate_entity_class(self, entity_class: Type[EntityType]):
        """Validate entity class"""
        if not entity_class:
            raise ValidationError("Entity class cannot be None")
    
    # ID generation
    def _generate_id(self) -> str:
        """Generate a new entity ID"""
        return str(uuid.uuid4())
    
    def _ensure_entity_id(self, entity: EntityType) -> str:
        """Ensure entity has an ID, generating one if needed"""
        if hasattr(entity, 'id') and entity.id:
            return entity.id
        
        entity_id = self._generate_id()
        if hasattr(entity, 'id'):
            entity.id = entity_id
        
        return entity_id
    
    # Transaction helpers
    def _create_transaction_context(self, isolation_level: str = "READ_COMMITTED") -> TransactionContext:
        """Create a new transaction context"""
        return TransactionContext(
            transaction_id=self._generate_id(),
            isolation_level=isolation_level
        )
    
    def _validate_transaction_context(self, context: Optional[TransactionContext]):
        """Validate transaction context"""
        if context and not context.is_active:
            raise TransactionError("Transaction context is not active")
    
    # Default implementations that can be overridden
    async def begin_transaction(self, isolation_level: str = "READ_COMMITTED") -> TransactionContext:
        """Begin a new transaction - default implementation"""
        context = self._create_transaction_context(isolation_level)
        context.is_active = True
        context.started_at = datetime.now()
        
        self._logger.debug(f"Transaction started: {context.transaction_id}")
        return context
    
    async def commit_transaction(self, context: TransactionContext):
        """Commit a transaction - default implementation"""
        self._validate_transaction_context(context)
        
        context.is_active = False
        context.is_committed = True
        context.committed_at = datetime.now()
        
        self._logger.debug(f"Transaction committed: {context.transaction_id}")
    
    async def rollback_transaction(self, context: TransactionContext):
        """Rollback a transaction - default implementation"""
        if context.is_active:
            context.is_active = False
            context.is_rolled_back = True
            
            self._logger.debug(f"Transaction rolled back: {context.transaction_id}")
    
    # Query helpers
    def _apply_filters(self, entities: List[EntityType], filters: List[QueryFilter]) -> List[EntityType]:
        """Apply filters to a list of entities (for in-memory filtering)"""
        if not filters:
            return entities
        
        filtered = []
        for entity in entities:
            if self._entity_matches_filters(entity, filters):
                filtered.append(entity)
        
        return filtered
    
    def _entity_matches_filters(self, entity: EntityType, filters: List[QueryFilter]) -> bool:
        """Check if entity matches all filters"""
        for filter_condition in filters:
            if not self._entity_matches_filter(entity, filter_condition):
                return False
        return True
    
    def _entity_matches_filter(self, entity: EntityType, filter_condition: QueryFilter) -> bool:
        """Check if entity matches a single filter"""
        try:
            # Get field value from entity
            field_value = getattr(entity, filter_condition.field, None)
            
            # Apply operator
            from .interface import QueryOperator
            op = filter_condition.operator
            value = filter_condition.value
            
            if op == QueryOperator.EQUALS:
                return field_value == value
            elif op == QueryOperator.NOT_EQUALS:
                return field_value != value
            elif op == QueryOperator.GREATER_THAN:
                return field_value is not None and field_value > value
            elif op == QueryOperator.GREATER_THAN_OR_EQUAL:
                return field_value is not None and field_value >= value
            elif op == QueryOperator.LESS_THAN:
                return field_value is not None and field_value < value
            elif op == QueryOperator.LESS_THAN_OR_EQUAL:
                return field_value is not None and field_value <= value
            elif op == QueryOperator.IN:
                return field_value in value if value else False
            elif op == QueryOperator.NOT_IN:
                return field_value not in value if value else True
            elif op == QueryOperator.CONTAINS:
                return isinstance(field_value, str) and isinstance(value, str) and value in field_value
            elif op == QueryOperator.STARTS_WITH:
                return isinstance(field_value, str) and isinstance(value, str) and field_value.startswith(value)
            elif op == QueryOperator.ENDS_WITH:
                return isinstance(field_value, str) and isinstance(value, str) and field_value.endswith(value)
            elif op == QueryOperator.IS_NULL:
                return field_value is None
            elif op == QueryOperator.IS_NOT_NULL:
                return field_value is not None
            else:
                return False
                
        except Exception as e:
            self._logger.warning(f"Filter evaluation failed: {e}")
            return False
    
    def _apply_sorting(self, entities: List[EntityType], options: QueryOptions) -> List[EntityType]:
        """Apply sorting to a list of entities"""
        if not options.sort_by:
            return entities
        
        def sort_key(entity):
            """Create sort key for entity"""
            key_parts = []
            for sort_criteria in options.sort_by:
                field_value = getattr(entity, sort_criteria.field, None)
                
                # Handle None values
                if field_value is None:
                    field_value = ""
                
                # Reverse for descending order
                from .interface import SortDirection
                if sort_criteria.direction == SortDirection.DESC:
                    if isinstance(field_value, (int, float)):
                        field_value = -field_value
                    elif isinstance(field_value, str):
                        # For strings, we'll sort separately
                        pass
                
                key_parts.append(field_value)
            
            return tuple(key_parts)
        
        # Sort with appropriate reverse setting
        reverse = False
        if options.sort_by:
            from .interface import SortDirection
            reverse = options.sort_by[0].direction == SortDirection.DESC
        
        return sorted(entities, key=sort_key, reverse=reverse)
    
    def _apply_pagination(self, entities: List[EntityType], options: QueryOptions) -> List[EntityType]:
        """Apply pagination to a list of entities"""
        start = options.offset
        
        if options.limit:
            end = start + options.limit
            return entities[start:end]
        else:
            return entities[start:]
    
    def _create_query_result(
        self, 
        entities: List[EntityType], 
        options: QueryOptions,
        total_count: Optional[int] = None,
        query_time_ms: Optional[float] = None
    ) -> QueryResult[EntityType]:
        """Create a query result with metadata"""
        has_more = False
        
        if options.limit and len(entities) == options.limit:
            # There might be more if we got exactly the limit
            has_more = True
        
        return QueryResult(
            entities=entities,
            total_count=total_count if options.include_count else None,
            has_more=has_more,
            query_time_ms=query_time_ms
        )

# Export main components
__all__ = [
    "BaseRepository", "RepositoryError", "EntityNotFoundError", 
    "TransactionError", "ValidationError", "RepositoryMetrics"
]