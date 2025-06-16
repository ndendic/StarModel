"""
Event Bus

Handles domain event publishing and subscription for SSE, WebSocket,
and multi-instance coordination.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, List, Dict, Any


class EventBus(ABC):
    """Abstract base class for event buses."""
    
    @abstractmethod
    async def publish(self, event: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        pass
    
    @abstractmethod
    def subscribe(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Subscribe a handler to receive events."""
        pass


class InProcessBus(EventBus):
    """
    Simple in-process event bus for single-instance applications.
    
    This implementation handles event publishing within a single process.
    For multi-instance deployments, this can be replaced with Redis pub/sub
    or other distributed event bus implementations.
    """
    
    def __init__(self):
        """Initialize the in-process event bus."""
        self._subscribers: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []
    
    def subscribe(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Subscribe a handler to receive all events.
        
        Args:
            handler: Async function that accepts event data
        """
        self._subscribers.append(handler)
    
    async def publish(self, event: Dict[str, Any]) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event data dictionary
        """
        if not self._subscribers:
            return
        
        # Publish to all subscribers concurrently
        tasks = [handler(event) for handler in self._subscribers]
        
        # Wait for all handlers to complete
        # Use gather with return_exceptions=True to prevent one handler
        # from blocking others if it raises an exception
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions that occurred during event handling
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # TODO: Add proper logging here
                print(f"Event handler {i} raised exception: {result}")
    
    def unsubscribe(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Unsubscribe a handler from receiving events.
        
        Args:
            handler: Handler function to remove
        """
        if handler in self._subscribers:
            self._subscribers.remove(handler)
    
    def clear_subscribers(self) -> None:
        """Remove all subscribers."""
        self._subscribers.clear()
    
    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)


# Example SSE handler for Datastar integration
async def datastar_event_handler(event: Dict[str, Any]) -> None:
    """
    Example event handler for Datastar SSE integration.
    
    This handler converts domain events into Datastar SSE responses.
    It should be registered with the event bus during application startup.
    
    Args:
        event: Domain event data
    """
    # TODO: Implement actual Datastar SSE response generation
    # This is where we would:
    # 1. Convert the event into appropriate Datastar fragments
    # 2. Send SSE updates to connected clients
    # 3. Handle client targeting based on entity scope
    
    entity_type = event.get('entity', '').split(':')[0]
    event_name = event.get('event')
    
    # For now, just print the event for debugging
    print(f"SSE Event: {entity_type}.{event_name} - {event}")


# Example WebSocket handler for real-time updates
async def websocket_event_handler(event: Dict[str, Any]) -> None:
    """
    Example event handler for WebSocket integration.
    
    This handler would send events to WebSocket connections for
    real-time updates in more complex scenarios.
    
    Args:
        event: Domain event data
    """
    # TODO: Implement WebSocket event broadcasting
    # This would be used for Phase 4 multi-instance coordination
    pass