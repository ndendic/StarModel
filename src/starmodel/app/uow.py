"""
Unit of Work Pattern

Manages transactions, persistence, and domain events in a coordinated way.
Ensures consistency across repository operations and event publishing.
"""

from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.entity import Entity
    from .bus import EventBus


class UnitOfWork:
    """
    Manages transactions and domain events.
    
    The Unit of Work pattern ensures that:
    1. Multiple repository operations are committed atomically
    2. Domain events are collected and published after successful commit
    3. Transactions can be rolled back if any operation fails
    """
    
    def __init__(self, bus: 'EventBus'):
        """
        Initialize Unit of Work.
        
        Args:
            bus: Event bus for publishing domain events
        """
        self.bus = bus
        self._events: List[Dict[str, Any]] = []
        self._committed = False
    
    def collect_event(self, event_data: Dict[str, Any]) -> None:
        """
        Collect a domain event to be published after commit.
        
        Args:
            event_data: Dictionary containing event information
        """
        self._events.append(event_data)
    
    async def commit(self, entity: 'Entity', command_record: Dict[str, Any]) -> None:
        """
        Commit entity state and publish collected domain events.
        
        Args:
            entity: Entity to persist
            command_record: Command record from dispatcher
        """
        try:
            if entity.persistence_backend:
                entity.persistence_backend.save_entity_sync(entity)            
            
            self.collect_event(command_record)
            
            # TODO: Add database transaction commit here for SQL repositories
            # if hasattr(repo, 'commit'):
            #     await repo.commit()
            self._committed = True
            await self._publish_events()
            
        except Exception as e:
            # TODO: Add rollback logic here
            # if hasattr(repo, 'rollback'):
            #     await repo.rollback()
            raise e
    
    async def _publish_events(self) -> None:
        """Publish all collected domain events to the event bus."""
        for event in self._events:
            await self.bus.publish(event)
        
        # Clear events after publishing
        self._events.clear()
    
    def rollback(self) -> None:
        """
        Rollback any uncommitted changes and clear collected events.
        
        Note: Actual rollback implementation depends on the repository type.
        """
        if not self._committed:
            self._events.clear()
            # TODO: Add repository-specific rollback logic
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic rollback on exception."""
        if exc_type is not None:
            self.rollback()