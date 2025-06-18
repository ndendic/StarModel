"""
StarModel Persistence Layer - Base Classes

This module provides abstract interfaces for entity persistence backends.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.entity import Entity

class EntityPersistenceBackend(ABC):
    """
    Abstract base class for entity persistence backends.
    
    Implementations must provide methods for saving, loading, and managing
    entity instances with optional TTL support and automatic cleanup.
    """
    
    def __init__(self):
        """Initialize persistence backend with cleanup configuration."""
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval: int = 300  # 5 minutes default
        self._auto_cleanup: bool = True
        self._running: bool = False
    
    @abstractmethod
    def save_entity_sync(self, entity: 'Entity', ttl: Optional[int] = None) -> bool:
        """
        Save entity instance to the persistence backend.
        
        Args:
            entity: Entity instance to persist
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def load_entity_sync(self, entity_id: str) -> Optional['Entity']:
        """
        Load entity instance from the persistence backend.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            Entity instance if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete_entity_sync(self, entity_id: str) -> bool:
        """
        Delete entity from the persistence backend.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def exists_sync(self, entity_id: str) -> bool:
        """
        Check if entity exists in the persistence backend.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            True if entity exists, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup_expired_sync(self) -> int:
        """
        Clean up expired entity entries.
        
        Returns:
            Number of entries cleaned up
        """
        pass
    
    def configure_cleanup(self, enabled: bool = True, interval: int = 300) -> None:
        """
        Configure automatic cleanup behavior.
        
        Args:
            enabled: Whether to enable automatic cleanup
            interval: Cleanup interval in seconds (default: 5 minutes)
        """
        self._auto_cleanup = enabled
        self._cleanup_interval = interval
        
        # Restart cleanup task if configuration changed and backend is running
        if self._running and self._cleanup_task:
            self.stop_cleanup()
            if enabled:
                self.start_cleanup()
    
    def start_cleanup(self) -> None:
        """Start the background cleanup task if auto_cleanup is enabled."""
        if not self._auto_cleanup or self._cleanup_task:
            return
            
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(self._cleanup_loop())
            self._running = True
        except RuntimeError:
            # No event loop running - cleanup will start when needed
            pass
    
    def stop_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        self._running = False
    
    async def _cleanup_loop(self) -> None:
        """Internal cleanup loop that runs periodically."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                cleaned = self.cleanup_expired_sync()
                if cleaned > 0:
                    print(f"{self.__class__.__name__}: Cleaned up {cleaned} expired entities")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"{self.__class__.__name__}: Error during cleanup: {e}")
                await asyncio.sleep(self._cleanup_interval)  # Continue despite errors