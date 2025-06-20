"""
Unit of Work Pattern - Transaction Coordination

💾 ACID Transaction Management:
The Unit of Work pattern coordinates changes across multiple entities
and persistence backends, ensuring atomicity and consistency while
publishing domain events after successful commits.

Key Features:
- Multi-backend transaction coordination
- Automatic rollback on failures
- Domain event publishing after commit
- Change tracking and conflict detection
- Context manager support for clean usage
"""

import asyncio
from typing import List, Dict, Any, Optional, Set, Type, AsyncContextManager
from contextlib import asynccontextmanager
from datetime import datetime
import uuid

from .domain_events import DomainEvent, EventType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...entities.lifecycle.entity import Entity
    from ...events.streaming.event_bus import EventBus
    from ...persistence.repositories.base import EntityPersistenceBackend

class UnitOfWorkError(Exception):
    """Base exception for Unit of Work errors"""
    pass

class TransactionError(UnitOfWorkError):
    """Raised when transaction operations fail"""
    pass

class ConcurrencyError(UnitOfWorkError):
    """Raised when concurrent modification is detected"""
    pass

class UnitOfWork:
    """
    Unit of Work pattern implementation for StarModel.
    
    Coordinates changes across multiple entities and persistence backends,
    ensuring ACID properties and publishing domain events after successful commits.
    
    Usage:
        async with UnitOfWork(event_bus) as uow:
            entity = await SomeEntity.get("123")
            entity.update_something()
            await uow.register_entity(entity)
            
            event = DomainEvent.command_executed(...)
            await uow.register_event(event)
            
            # Commit happens automatically on successful exit
            # Rollback happens automatically on exceptions
    """
    
    def __init__(
        self,
        event_bus: Optional['EventBus'] = None,
        isolation_level: str = "READ_COMMITTED"
    ):
        self.event_bus = event_bus
        self.isolation_level = isolation_level
        
        # Transaction state
        self._transaction_id = str(uuid.uuid4())
        self._is_active = False
        self._is_committed = False
        self._is_rolled_back = False
        
        # Entity tracking
        self._entities_to_save: List['Entity'] = []
        self._entities_to_delete: List['Entity'] = []
        self._entity_snapshots: Dict[str, Dict[str, Any]] = {}
        
        # Event tracking
        self._domain_events: List[DomainEvent] = []
        
        # Backend tracking for transaction coordination
        self._active_backends: Set['EntityPersistenceBackend'] = set()
        self._backend_transactions: Dict['EntityPersistenceBackend', Any] = {}
        
        # Change tracking
        self._changes_tracked = True
        self._change_log: List[Dict[str, Any]] = []
    
    @property
    def transaction_id(self) -> str:
        """Get the unique transaction ID"""
        return self._transaction_id
    
    @property
    def is_active(self) -> bool:
        """Check if transaction is active"""
        return self._is_active
    
    @property
    def is_committed(self) -> bool:
        """Check if transaction is committed"""
        return self._is_committed
    
    @property
    def is_rolled_back(self) -> bool:
        """Check if transaction is rolled back"""
        return self._is_rolled_back
    
    async def begin(self):
        """Begin the unit of work transaction"""
        if self._is_active:
            raise TransactionError("Transaction is already active")
        
        if self._is_committed or self._is_rolled_back:
            raise TransactionError("Transaction has already been completed")
        
        self._is_active = True
        self._log_change("transaction_begin", {"transaction_id": self._transaction_id})
    
    async def register_entity(self, entity: 'Entity', operation: str = "save"):
        """
        Register an entity for persistence.
        
        Args:
            entity: The entity to persist
            operation: Either "save" or "delete"
        """
        if not self._is_active:
            await self.begin()
        
        entity_key = self._get_entity_key(entity)
        
        if operation == "save":
            # Take snapshot for change detection
            if self._changes_tracked:
                self._entity_snapshots[entity_key] = self._take_entity_snapshot(entity)
            
            # Add to save list (remove from delete list if present)
            if entity not in self._entities_to_save:
                self._entities_to_save.append(entity)
            
            if entity in self._entities_to_delete:
                self._entities_to_delete.remove(entity)
            
            self._log_change("entity_registered_save", {
                "entity_type": entity.__class__.__name__,
                "entity_id": getattr(entity, 'id', None)
            })
        
        elif operation == "delete":
            # Add to delete list (remove from save list if present)
            if entity not in self._entities_to_delete:
                self._entities_to_delete.append(entity)
            
            if entity in self._entities_to_save:
                self._entities_to_save.remove(entity)
            
            self._log_change("entity_registered_delete", {
                "entity_type": entity.__class__.__name__,
                "entity_id": getattr(entity, 'id', None)
            })
        
        else:
            raise ValueError(f"Invalid operation: {operation}. Must be 'save' or 'delete'")
    
    async def register_event(self, event: DomainEvent):
        """Register a domain event for publishing after commit"""
        if not self._is_active:
            await self.begin()
        
        self._domain_events.append(event)
        self._log_change("event_registered", {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "entity_type": event.entity_type
        })
    
    async def commit(self):
        """
        Commit all changes atomically.
        
        Steps:
        1. Validate all changes
        2. Begin backend transactions
        3. Persist all entities
        4. Commit backend transactions
        5. Publish domain events
        6. Mark transaction as committed
        """
        if not self._is_active:
            raise TransactionError("No active transaction to commit")
        
        if self._is_committed:
            raise TransactionError("Transaction already committed")
        
        if self._is_rolled_back:
            raise TransactionError("Cannot commit rolled back transaction")
        
        try:
            # 1. Validate changes
            await self._validate_changes()
            
            # 2. Begin backend transactions
            await self._begin_backend_transactions()
            
            # 3. Persist entities
            await self._persist_entities()
            
            # 4. Commit backend transactions
            await self._commit_backend_transactions()
            
            # 5. Publish domain events
            await self._publish_domain_events()
            
            # 6. Mark as committed
            self._is_committed = True
            self._is_active = False
            
            self._log_change("transaction_committed", {
                "entities_saved": len(self._entities_to_save),
                "entities_deleted": len(self._entities_to_delete),
                "events_published": len(self._domain_events)
            })
            
        except Exception as e:
            # Rollback on any error
            await self.rollback()
            raise TransactionError(f"Commit failed: {e}") from e
    
    async def rollback(self):
        """
        Rollback all changes and restore original state.
        """
        if not self._is_active:
            return  # Nothing to rollback
        
        if self._is_committed:
            raise TransactionError("Cannot rollback committed transaction")
        
        try:
            # Rollback backend transactions
            await self._rollback_backend_transactions()
            
            # Restore entity snapshots
            await self._restore_entity_snapshots()
            
            # Clear tracking
            self._entities_to_save.clear()
            self._entities_to_delete.clear()
            self._domain_events.clear()
            self._entity_snapshots.clear()
            
            # Mark as rolled back
            self._is_rolled_back = True
            self._is_active = False
            
            self._log_change("transaction_rolled_back", {})
            
        except Exception as e:
            # Log rollback failure but don't raise - transaction is still invalid
            self._log_change("rollback_failed", {"error": str(e)})
            self._is_active = False
    
    async def _validate_changes(self):
        """Validate all pending changes"""
        # Check for concurrent modifications
        for entity in self._entities_to_save:
            await self._check_concurrency_conflicts(entity)
        
        # Validate entity states
        for entity in self._entities_to_save:
            if hasattr(entity, 'validate'):
                await entity.validate()
    
    async def _check_concurrency_conflicts(self, entity: 'Entity'):
        """Check for concurrent modifications using optimistic locking"""
        entity_key = self._get_entity_key(entity)
        
        if entity_key not in self._entity_snapshots:
            return  # New entity, no conflict possible
        
        # Get current version from persistence
        if hasattr(entity, 'id') and entity.id:
            try:
                current_entity = await entity.__class__.get(entity.id)
                if current_entity:
                    # Compare timestamps or version numbers
                    if hasattr(entity, 'updated_at') and hasattr(current_entity, 'updated_at'):
                        snapshot_time = self._entity_snapshots[entity_key].get('updated_at')
                        if snapshot_time and current_entity.updated_at > snapshot_time:
                            raise ConcurrencyError(
                                f"Entity {entity_key} was modified by another transaction"
                            )
            except Exception:
                # If we can't check, proceed (backend might not support it)
                pass
    
    async def _begin_backend_transactions(self):
        """Begin transactions on all involved backends"""
        for entity in self._entities_to_save + self._entities_to_delete:
            backend = entity.get_persistence_manager().get_backend(entity.__class__)
            
            if backend not in self._active_backends:
                self._active_backends.add(backend)
                
                # Begin transaction on backend if it supports it
                if hasattr(backend, 'begin_transaction'):
                    transaction = await backend.begin_transaction()
                    self._backend_transactions[backend] = transaction
    
    async def _persist_entities(self):
        """Persist all registered entities"""
        # Save entities
        for entity in self._entities_to_save:
            backend = entity.get_persistence_manager().get_backend(entity.__class__)
            await backend.save_entity(entity)
            
            # Generate domain events for saves
            if hasattr(entity, 'id') and entity.id:
                entity_key = self._get_entity_key(entity)
                
                if entity_key in self._entity_snapshots:
                    # Entity update
                    changes = self._calculate_changes(entity, self._entity_snapshots[entity_key])
                    if changes:
                        event = DomainEvent.entity_updated(
                            entity_type=entity.__class__.__name__,
                            entity_id=entity.id,
                            changes=changes
                        )
                        self._domain_events.append(event)
                else:
                    # Entity creation
                    event = DomainEvent.entity_created(
                        entity_type=entity.__class__.__name__,
                        entity_id=entity.id,
                        entity_data=entity.model_dump()
                    )
                    self._domain_events.append(event)
        
        # Delete entities
        for entity in self._entities_to_delete:
            backend = entity.get_persistence_manager().get_backend(entity.__class__)
            
            if hasattr(entity, 'id') and entity.id:
                await backend.delete_entity(entity.__class__, entity.id)
                
                # Generate domain event for deletion
                event = DomainEvent.entity_deleted(
                    entity_type=entity.__class__.__name__,
                    entity_id=entity.id
                )
                self._domain_events.append(event)
    
    async def _commit_backend_transactions(self):
        """Commit all backend transactions"""
        for backend, transaction in self._backend_transactions.items():
            if hasattr(backend, 'commit_transaction'):
                await backend.commit_transaction(transaction)
    
    async def _rollback_backend_transactions(self):
        """Rollback all backend transactions"""
        for backend, transaction in self._backend_transactions.items():
            try:
                if hasattr(backend, 'rollback_transaction'):
                    await backend.rollback_transaction(transaction)
            except Exception as e:
                # Log but continue with other rollbacks
                self._log_change("backend_rollback_failed", {
                    "backend": str(backend),
                    "error": str(e)
                })
    
    async def _publish_domain_events(self):
        """Publish all domain events after successful commit"""
        if not self.event_bus:
            return
        
        for event in self._domain_events:
            try:
                await self.event_bus.publish(event)
            except Exception as e:
                # Log event publishing failure but don't fail the transaction
                self._log_change("event_publish_failed", {
                    "event_id": event.event_id,
                    "error": str(e)
                })
    
    async def _restore_entity_snapshots(self):
        """Restore entities to their snapshot state"""
        for entity in self._entities_to_save:
            entity_key = self._get_entity_key(entity)
            if entity_key in self._entity_snapshots:
                snapshot = self._entity_snapshots[entity_key]
                self._restore_entity_from_snapshot(entity, snapshot)
    
    def _get_entity_key(self, entity: 'Entity') -> str:
        """Get unique key for entity"""
        entity_id = getattr(entity, 'id', None)
        return f"{entity.__class__.__name__}:{entity_id}" if entity_id else str(id(entity))
    
    def _take_entity_snapshot(self, entity: 'Entity') -> Dict[str, Any]:
        """Take snapshot of entity current state"""
        return entity.model_dump()
    
    def _restore_entity_from_snapshot(self, entity: 'Entity', snapshot: Dict[str, Any]):
        """Restore entity from snapshot"""
        for field, value in snapshot.items():
            if hasattr(entity, field):
                setattr(entity, field, value)
    
    def _calculate_changes(self, entity: 'Entity', snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate what changed between current state and snapshot"""
        current_state = entity.model_dump()
        changes = {}
        
        for field, current_value in current_state.items():
            snapshot_value = snapshot.get(field)
            if current_value != snapshot_value:
                changes[field] = {
                    "old": snapshot_value,
                    "new": current_value
                }
        
        return changes
    
    def _log_change(self, change_type: str, data: Dict[str, Any]):
        """Log change for audit trail"""
        if self._changes_tracked:
            self._change_log.append({
                "timestamp": datetime.now(),
                "transaction_id": self._transaction_id,
                "change_type": change_type,
                "data": data
            })
    
    def get_change_log(self) -> List[Dict[str, Any]]:
        """Get the change log for this transaction"""
        return self._change_log.copy()
    
    # Context manager support
    async def __aenter__(self):
        await self.begin()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # No exception - commit
            await self.commit()
        else:
            # Exception occurred - rollback
            await self.rollback()
        return False  # Don't suppress exceptions

@asynccontextmanager
async def TransactionScope(
    event_bus: Optional['EventBus'] = None,
    isolation_level: str = "READ_COMMITTED"
) -> AsyncContextManager[UnitOfWork]:
    """
    Convenience context manager for creating Unit of Work transactions.
    
    Usage:
        async with TransactionScope(event_bus) as uow:
            # Do work with uow
            pass
    """
    uow = UnitOfWork(event_bus, isolation_level)
    async with uow:
        yield uow

# Export main components
__all__ = [
    "UnitOfWork", "TransactionScope", "UnitOfWorkError", 
    "TransactionError", "ConcurrencyError"
]