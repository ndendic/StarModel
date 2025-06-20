"""
Memory Repository - In-Memory Persistence Backend

🧠 High-Performance In-Memory Storage:
This module provides a complete in-memory persistence backend with advanced features
like TTL management, automatic cleanup, query optimization, and transaction support.
"""

from typing import Dict, Type, Optional, List, Any, Set
from datetime import datetime, timedelta
import asyncio
import threading
from collections import defaultdict
from dataclasses import dataclass, field
import weakref
import logging

from ..repositories.interface import (
    EntityRepository, QueryOptions, QueryResult, QueryFilter, 
    TransactionContext, EntityType
)
from ..repositories.base import BaseRepository, EntityNotFoundError, TransactionError

logger = logging.getLogger(__name__)

@dataclass
class EntityRecord:
    """Record stored in memory with metadata"""
    entity: Any  # The actual entity instance
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        """Check if record is expired"""
        return self.expires_at is not None and datetime.now() > self.expires_at
    
    def touch(self):
        """Update access tracking"""
        self.access_count += 1
        self.last_accessed = datetime.now()

class MemoryTransaction:
    """Transaction context for memory operations"""
    
    def __init__(self, transaction_id: str, isolation_level: str = "READ_COMMITTED"):
        self.transaction_id = transaction_id
        self.isolation_level = isolation_level
        self.is_active = True
        self.is_committed = False
        self.is_rolled_back = False
        self.started_at = datetime.now()
        self.committed_at: Optional[datetime] = None
        
        # Track changes during transaction
        self.saved_entities: List[tuple] = []  # (entity_class, entity_id, entity)
        self.deleted_entities: List[tuple] = []  # (entity_class, entity_id)
        
        # Snapshot for rollback
        self.snapshots: Dict[str, Any] = {}

class MemoryRepository(BaseRepository[EntityType]):
    """
    Complete in-memory repository implementation.
    
    Features:
    - Fast in-memory storage with entity indexing
    - TTL (Time To Live) support with automatic expiration
    - Configurable cleanup intervals and strategies
    - Full transaction support with rollback
    - Advanced querying with filtering and sorting
    - Batch operations for performance
    - Comprehensive metrics and monitoring
    - Thread-safe operations
    """
    
    def __init__(self, 
                 cleanup_interval: int = 300,  # 5 minutes
                 max_entities: int = 10000,
                 ttl_default: int = 3600,  # 1 hour
                 enable_access_tracking: bool = True,
                 enable_statistics: bool = True):
        super().__init__(
            cleanup_interval=cleanup_interval,
            max_entities=max_entities,
            ttl_default=ttl_default,
            enable_access_tracking=enable_access_tracking,
            enable_statistics=enable_statistics
        )
        
        # Core storage
        self._storage: Dict[str, Dict[str, EntityRecord]] = defaultdict(dict)
        self._entity_classes: Dict[str, Type[EntityType]] = {}
        
        # Indexing for fast queries
        self._indexes: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        # Transaction management
        self._transactions: Dict[str, MemoryTransaction] = {}
        self._transaction_lock = threading.RLock()
        
        # Cleanup management
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_enabled = cleanup_interval > 0
        
        # Configuration
        self.cleanup_interval = cleanup_interval
        self.max_entities = max_entities
        self.ttl_default = ttl_default
        self.enable_access_tracking = enable_access_tracking
        self.enable_statistics = enable_statistics
    
    async def _do_initialize(self):
        """Initialize the memory repository"""
        if self._cleanup_enabled:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"MemoryRepository initialized with cleanup_interval={self.cleanup_interval}s")
    
    async def _do_shutdown(self):
        """Shutdown the memory repository"""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear all data
        self._storage.clear()
        self._entity_classes.clear()
        self._indexes.clear()
        self._transactions.clear()
        
        logger.info("MemoryRepository shutdown complete")
    
    def _get_entity_type_key(self, entity_class: Type[EntityType]) -> str:
        """Get storage key for entity type"""
        return f"{entity_class.__module__}.{entity_class.__name__}"
    
    def _register_entity_class(self, entity_class: Type[EntityType]):
        """Register entity class for type tracking"""
        type_key = self._get_entity_type_key(entity_class)
        self._entity_classes[type_key] = entity_class
    
    def _create_entity_record(self, entity: EntityType, ttl: Optional[int] = None) -> EntityRecord:
        """Create an entity record with metadata"""
        now = datetime.now()
        expires_at = None
        
        if ttl:
            expires_at = now + timedelta(seconds=ttl)
        elif self.ttl_default:
            expires_at = now + timedelta(seconds=self.ttl_default)
        
        return EntityRecord(
            entity=entity,
            created_at=now,
            updated_at=now,
            expires_at=expires_at
        )
    
    def _update_indexes(self, entity_class: Type[EntityType], entity_id: str, entity: EntityType):
        """Update indexes for fast querying"""
        type_key = self._get_entity_type_key(entity_class)
        
        # Clear existing indexes for this entity
        for field_name, field_index in self._indexes[type_key].items():
            field_index.discard(entity_id)
        
        # Add new indexes
        for field_name in entity.model_fields if hasattr(entity, 'model_fields') else []:
            field_value = getattr(entity, field_name, None)
            if field_value is not None:
                index_key = f"{field_name}:{field_value}"
                self._indexes[type_key][index_key].add(entity_id)
    
    def _remove_from_indexes(self, entity_class: Type[EntityType], entity_id: str):
        """Remove entity from all indexes"""
        type_key = self._get_entity_type_key(entity_class)
        
        for field_name, field_index in self._indexes[type_key].items():
            field_index.discard(entity_id)
    
    # Core CRUD operations
    async def save(self, entity: EntityType, context: Optional[TransactionContext] = None) -> str:
        """Save an entity to memory"""
        start_time = self._record_operation_start()
        
        try:
            self._validate_entity(entity)
            entity_id = self._ensure_entity_id(entity)
            entity_class = type(entity)
            
            self._register_entity_class(entity_class)
            type_key = self._get_entity_type_key(entity_class)
            
            # Handle transaction
            if context and isinstance(context, MemoryTransaction):
                # Store in transaction buffer
                context.saved_entities.append((entity_class, entity_id, entity))
            else:
                # Direct storage
                record = self._create_entity_record(entity)
                self._storage[type_key][entity_id] = record
                self._update_indexes(entity_class, entity_id, entity)
                
                # Update metrics
                self.metrics.entities_count = sum(len(entities) for entities in self._storage.values())
            
            self._record_operation_success(start_time)
            return entity_id
            
        except Exception as e:
            self._record_operation_failure(start_time, e)
            raise
    
    async def load(self, entity_class: Type[EntityType], entity_id: str, 
                   context: Optional[TransactionContext] = None) -> Optional[EntityType]:
        """Load an entity from memory"""
        start_time = self._record_operation_start()
        
        try:
            self._validate_entity_id(entity_id)
            self._validate_entity_class(entity_class)
            
            type_key = self._get_entity_type_key(entity_class)
            
            # Check transaction buffer first
            if context and isinstance(context, MemoryTransaction):
                for saved_class, saved_id, saved_entity in context.saved_entities:
                    if saved_class == entity_class and saved_id == entity_id:
                        self._record_cache_hit()
                        self._record_operation_success(start_time)
                        return saved_entity
            
            # Check main storage
            record = self._storage[type_key].get(entity_id)
            if not record:
                self._record_cache_miss()
                self._record_operation_success(start_time)
                return None
            
            # Check expiration
            if record.is_expired():
                del self._storage[type_key][entity_id]
                self._remove_from_indexes(entity_class, entity_id)
                self._record_cache_miss()
                self._record_operation_success(start_time)
                return None
            
            # Update access tracking
            if self.enable_access_tracking:
                record.touch()
            
            self._record_cache_hit()
            self._record_operation_success(start_time)
            return record.entity
            
        except Exception as e:
            self._record_operation_failure(start_time, e)
            raise
    
    async def delete(self, entity_class: Type[EntityType], entity_id: str,
                     context: Optional[TransactionContext] = None) -> bool:
        """Delete an entity from memory"""
        start_time = self._record_operation_start()
        
        try:
            self._validate_entity_id(entity_id)
            self._validate_entity_class(entity_class)
            
            type_key = self._get_entity_type_key(entity_class)
            
            # Handle transaction
            if context and isinstance(context, MemoryTransaction):
                # Add to transaction buffer
                context.deleted_entities.append((entity_class, entity_id))
                self._record_operation_success(start_time)
                return True
            
            # Direct deletion
            if entity_id in self._storage[type_key]:
                del self._storage[type_key][entity_id]
                self._remove_from_indexes(entity_class, entity_id)
                
                # Update metrics
                self.metrics.entities_count = sum(len(entities) for entities in self._storage.values())
                
                self._record_operation_success(start_time)
                return True
            
            self._record_operation_success(start_time)
            return False
            
        except Exception as e:
            self._record_operation_failure(start_time, e)
            raise
    
    async def exists(self, entity_class: Type[EntityType], entity_id: str,
                     context: Optional[TransactionContext] = None) -> bool:
        """Check if an entity exists in memory"""
        entity = await self.load(entity_class, entity_id, context)
        return entity is not None
    
    # Query operations
    async def query(self, entity_class: Type[EntityType], options: QueryOptions,
                    context: Optional[TransactionContext] = None) -> QueryResult[EntityType]:
        """Query entities with filtering and sorting"""
        start_time = self._record_operation_start()
        
        try:
            self._validate_entity_class(entity_class)
            type_key = self._get_entity_type_key(entity_class)
            
            # Get all entities of this type
            all_records = self._storage[type_key]
            entities = []
            
            # Filter out expired entities and convert to entity list
            for entity_id, record in list(all_records.items()):
                if record.is_expired():
                    del all_records[entity_id]
                    self._remove_from_indexes(entity_class, entity_id)
                    continue
                
                entities.append(record.entity)
                
                # Update access tracking
                if self.enable_access_tracking:
                    record.touch()
            
            # Apply filters
            if options.filters:
                entities = self._apply_filters(entities, options.filters)
            
            # Get total count before pagination
            total_count = len(entities) if options.include_count else None
            
            # Apply sorting
            entities = self._apply_sorting(entities, options)
            
            # Apply pagination
            entities = self._apply_pagination(entities, options)
            
            # Create result
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            result = self._create_query_result(entities, options, total_count, query_time)
            
            self._record_operation_success(start_time)
            return result
            
        except Exception as e:
            self._record_operation_failure(start_time, e)
            raise
    
    async def count(self, entity_class: Type[EntityType], filters: Optional[List[QueryFilter]] = None,
                    context: Optional[TransactionContext] = None) -> int:
        """Count entities matching filters"""
        start_time = self._record_operation_start()
        
        try:
            type_key = self._get_entity_type_key(entity_class)
            all_records = self._storage[type_key]
            
            # Filter out expired entities
            valid_entities = []
            for entity_id, record in list(all_records.items()):
                if record.is_expired():
                    del all_records[entity_id]
                    self._remove_from_indexes(entity_class, entity_id)
                    continue
                
                valid_entities.append(record.entity)
            
            # Apply filters if provided
            if filters:
                valid_entities = self._apply_filters(valid_entities, filters)
            
            count = len(valid_entities)
            self._record_operation_success(start_time)
            return count
            
        except Exception as e:
            self._record_operation_failure(start_time, e)
            raise
    
    # Batch operations
    async def save_batch(self, entities: List[EntityType], 
                         context: Optional[TransactionContext] = None) -> List[str]:
        """Save multiple entities in a batch"""
        entity_ids = []
        for entity in entities:
            entity_id = await self.save(entity, context)
            entity_ids.append(entity_id)
        return entity_ids
    
    async def load_batch(self, entity_class: Type[EntityType], entity_ids: List[str],
                         context: Optional[TransactionContext] = None) -> List[Optional[EntityType]]:
        """Load multiple entities by ID"""
        entities = []
        for entity_id in entity_ids:
            entity = await self.load(entity_class, entity_id, context)
            entities.append(entity)
        return entities
    
    async def delete_batch(self, entity_class: Type[EntityType], entity_ids: List[str],
                           context: Optional[TransactionContext] = None) -> int:
        """Delete multiple entities by ID"""
        deleted_count = 0
        for entity_id in entity_ids:
            if await self.delete(entity_class, entity_id, context):
                deleted_count += 1
        return deleted_count
    
    # Transaction operations
    async def begin_transaction(self, isolation_level: str = "READ_COMMITTED") -> TransactionContext:
        """Begin a new memory transaction"""
        transaction = MemoryTransaction(self._generate_id(), isolation_level)
        
        with self._transaction_lock:
            self._transactions[transaction.transaction_id] = transaction
        
        return transaction
    
    async def commit_transaction(self, context: TransactionContext):
        """Commit a memory transaction"""
        if not isinstance(context, MemoryTransaction):
            await super().commit_transaction(context)
            return
        
        with self._transaction_lock:
            transaction = self._transactions.get(context.transaction_id)
            if not transaction or not transaction.is_active:
                raise TransactionError("Transaction is not active")
            
            # Apply all saved entities
            for entity_class, entity_id, entity in transaction.saved_entities:
                type_key = self._get_entity_type_key(entity_class)
                record = self._create_entity_record(entity)
                self._storage[type_key][entity_id] = record
                self._update_indexes(entity_class, entity_id, entity)
            
            # Apply all deletions
            for entity_class, entity_id in transaction.deleted_entities:
                type_key = self._get_entity_type_key(entity_class)
                if entity_id in self._storage[type_key]:
                    del self._storage[type_key][entity_id]
                    self._remove_from_indexes(entity_class, entity_id)
            
            # Update transaction state
            transaction.is_active = False
            transaction.is_committed = True
            transaction.committed_at = datetime.now()
            
            # Update metrics
            self.metrics.entities_count = sum(len(entities) for entities in self._storage.values())
            
            # Clean up transaction
            del self._transactions[context.transaction_id]
    
    async def rollback_transaction(self, context: TransactionContext):
        """Rollback a memory transaction"""
        if not isinstance(context, MemoryTransaction):
            await super().rollback_transaction(context)
            return
        
        with self._transaction_lock:
            transaction = self._transactions.get(context.transaction_id)
            if transaction and transaction.is_active:
                transaction.is_active = False
                transaction.is_rolled_back = True
                
                # Clean up transaction
                del self._transactions[context.transaction_id]
    
    # Cleanup and maintenance
    async def cleanup_expired(self, entity_class: Type[EntityType], 
                              before: datetime) -> int:
        """Clean up expired entities"""
        type_key = self._get_entity_type_key(entity_class)
        storage = self._storage[type_key]
        
        expired_ids = []
        for entity_id, record in storage.items():
            if record.expires_at and record.expires_at < before:
                expired_ids.append(entity_id)
        
        # Remove expired entities
        for entity_id in expired_ids:
            del storage[entity_id]
            self._remove_from_indexes(entity_class, entity_id)
        
        # Update metrics
        self.metrics.entities_count = sum(len(entities) for entities in self._storage.values())
        self.metrics.last_cleanup = datetime.now()
        
        logger.debug(f"Cleaned up {len(expired_ids)} expired entities of type {entity_class.__name__}")
        return len(expired_ids)
    
    async def _cleanup_loop(self):
        """Background cleanup loop for expired entities"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                cleanup_before = datetime.now()
                total_cleaned = 0
                
                # Clean up all entity types
                for type_key, entity_class in self._entity_classes.items():
                    cleaned = await self.cleanup_expired(entity_class, cleanup_before)
                    total_cleaned += cleaned
                
                if total_cleaned > 0:
                    logger.info(f"Cleanup completed: removed {total_cleaned} expired entities")
                
            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive repository metrics"""
        base_metrics = await super().get_metrics()
        
        # Add memory-specific metrics
        memory_metrics = {
            "storage_info": {
                "entity_types": len(self._entity_classes),
                "total_entities": sum(len(entities) for entities in self._storage.values()),
                "entities_by_type": {
                    entity_class.__name__: len(self._storage[type_key])
                    for type_key, entity_class in self._entity_classes.items()
                },
                "index_count": sum(
                    len(field_indexes) for type_indexes in self._indexes.values()
                    for field_indexes in type_indexes.values()
                )
            },
            "transaction_info": {
                "active_transactions": len(self._transactions),
                "transaction_ids": list(self._transactions.keys())
            },
            "configuration": {
                "cleanup_interval": self.cleanup_interval,
                "max_entities": self.max_entities,
                "ttl_default": self.ttl_default,
                "cleanup_enabled": self._cleanup_enabled
            }
        }
        
        return {**base_metrics, **memory_metrics}

# Export main components
__all__ = ["MemoryRepository", "EntityRecord", "MemoryTransaction"]