"""
Event Bus - Pub/Sub Infrastructure

🚀 Reactive Event Publishing:
The event bus provides a clean pub/sub infrastructure for domain events,
enabling loose coupling between system components and reactive patterns.

Key Features:
- Abstract event bus interface for pluggability
- In-process implementation for single-server scenarios
- Async/await support for all operations
- Event filtering and routing capabilities
- Error isolation between subscribers
- Metrics and monitoring support
"""

import asyncio
from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Callable, Union, Set,
    AsyncIterator, TypeVar, Generic
)
from collections import defaultdict
from datetime import datetime
import uuid
import weakref

from ...persistence.transactions.domain_events import DomainEvent, EventType

# Type definitions
EventHandler = Union[Callable[[DomainEvent], Any], Callable[[DomainEvent], asyncio.coroutine]]
EventFilter = Callable[[DomainEvent], bool]

T = TypeVar('T')

class EventBusError(Exception):
    """Base exception for event bus errors"""
    pass

class SubscriptionError(EventBusError):
    """Raised when subscription operations fail"""
    pass

class PublishingError(EventBusError):
    """Raised when event publishing fails"""
    pass

class EventBusMetrics:
    """Metrics tracking for event bus operations"""
    
    def __init__(self):
        self.events_published = 0
        self.events_delivered = 0
        self.subscription_count = 0
        self.handler_errors = 0
        self.total_publish_time_ms = 0.0
        self.start_time = datetime.now()
    
    def record_publish(self, delivery_count: int, duration_ms: float):
        """Record a publish operation"""
        self.events_published += 1
        self.events_delivered += delivery_count
        self.total_publish_time_ms += duration_ms
    
    def record_subscription(self):
        """Record a new subscription"""
        self.subscription_count += 1
    
    def record_handler_error(self):
        """Record a handler error"""
        self.handler_errors += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "uptime_seconds": uptime_seconds,
            "events_published": self.events_published,
            "events_delivered": self.events_delivered,
            "subscription_count": self.subscription_count,
            "handler_errors": self.handler_errors,
            "average_publish_time_ms": (
                self.total_publish_time_ms / self.events_published 
                if self.events_published > 0 else 0
            ),
            "events_per_second": (
                self.events_published / uptime_seconds 
                if uptime_seconds > 0 else 0
            ),
            "error_rate": (
                self.handler_errors / self.events_delivered 
                if self.events_delivered > 0 else 0
            )
        }

class Subscription:
    """Represents a subscription to events"""
    
    def __init__(
        self,
        subscription_id: str,
        handler: EventHandler,
        event_filter: Optional[EventFilter] = None,
        priority: int = 0
    ):
        self.subscription_id = subscription_id
        self.handler = handler
        self.event_filter = event_filter
        self.priority = priority
        self.created_at = datetime.now()
        self.events_handled = 0
        self.last_event_at: Optional[datetime] = None
        self.errors = 0
    
    def should_handle(self, event: DomainEvent) -> bool:
        """Check if this subscription should handle the event"""
        if self.event_filter:
            try:
                return self.event_filter(event)
            except Exception:
                # If filter fails, default to not handling
                return False
        return True
    
    async def handle_event(self, event: DomainEvent):
        """Handle an event with error tracking"""
        try:
            if asyncio.iscoroutinefunction(self.handler):
                await self.handler(event)
            else:
                self.handler(event)
            
            self.events_handled += 1
            self.last_event_at = datetime.now()
            
        except Exception as e:
            self.errors += 1
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        return {
            "subscription_id": self.subscription_id,
            "created_at": self.created_at,
            "events_handled": self.events_handled,
            "last_event_at": self.last_event_at,
            "errors": self.errors,
            "priority": self.priority
        }

class EventBus(ABC):
    """
    Abstract event bus interface.
    
    Provides a contract for event publishing and subscription
    that can be implemented by different transport mechanisms
    (in-process, Redis, RabbitMQ, etc.).
    """
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> bool:
        """
        Publish an event to all subscribers.
        
        Args:
            event: The domain event to publish
            
        Returns:
            bool: True if published successfully
        """
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        handler: EventHandler,
        event_types: Optional[List[EventType]] = None,
        entity_types: Optional[List[str]] = None,
        event_filter: Optional[EventFilter] = None,
        priority: int = 0
    ) -> str:
        """
        Subscribe to events with optional filtering.
        
        Args:
            handler: Function to handle events
            event_types: List of event types to subscribe to
            entity_types: List of entity types to subscribe to
            event_filter: Custom filter function
            priority: Handler priority (higher = called first)
            
        Returns:
            str: Subscription ID for later unsubscribing
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: ID returned from subscribe()
            
        Returns:
            bool: True if unsubscribed successfully
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics"""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """Shutdown the event bus gracefully"""
        pass

class InProcessEventBus(EventBus):
    """
    In-process event bus implementation.
    
    Suitable for single-server deployments or development.
    Events are delivered synchronously to all subscribers
    with error isolation between handlers.
    """
    
    def __init__(self, max_concurrent_handlers: int = 100):
        self.max_concurrent_handlers = max_concurrent_handlers
        self.metrics = EventBusMetrics()
        
        # Subscription management
        self._subscriptions: Dict[str, Subscription] = {}
        self._type_subscriptions: Dict[EventType, List[str]] = defaultdict(list)
        self._entity_subscriptions: Dict[str, List[str]] = defaultdict(list)
        self._global_subscriptions: List[str] = []
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent_handlers)
        self._shutdown_event = asyncio.Event()
        
        # Weak references to prevent memory leaks
        self._weak_handlers: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
    
    async def publish(self, event: DomainEvent) -> bool:
        """Publish event to all matching subscribers"""
        if self._shutdown_event.is_set():
            raise PublishingError("Event bus is shut down")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Find all matching subscriptions
            subscription_ids = self._find_matching_subscriptions(event)
            
            if not subscription_ids:
                return True  # No subscribers is not an error
            
            # Sort by priority (higher priority first)
            subscriptions = [
                self._subscriptions[sub_id] 
                for sub_id in subscription_ids 
                if sub_id in self._subscriptions
            ]
            subscriptions.sort(key=lambda s: s.priority, reverse=True)
            
            # Deliver to all subscribers concurrently
            tasks = []
            for subscription in subscriptions:
                task = self._deliver_to_subscription(subscription, event)
                tasks.append(task)
            
            # Wait for all deliveries (with error isolation)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful deliveries
            successful_deliveries = sum(1 for result in results if not isinstance(result, Exception))
            
            # Record metrics
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.record_publish(successful_deliveries, duration_ms)
            
            return successful_deliveries > 0
            
        except Exception as e:
            raise PublishingError(f"Failed to publish event: {e}") from e
    
    async def subscribe(
        self,
        handler: EventHandler,
        event_types: Optional[List[EventType]] = None,
        entity_types: Optional[List[str]] = None,
        event_filter: Optional[EventFilter] = None,
        priority: int = 0
    ) -> str:
        """Subscribe to events with filtering"""
        subscription_id = str(uuid.uuid4())
        
        # Create subscription
        subscription = Subscription(
            subscription_id=subscription_id,
            handler=handler,
            event_filter=event_filter,
            priority=priority
        )
        
        # Store subscription
        self._subscriptions[subscription_id] = subscription
        
        # Index by event types
        if event_types:
            for event_type in event_types:
                self._type_subscriptions[event_type].append(subscription_id)
        
        # Index by entity types
        if entity_types:
            for entity_type in entity_types:
                self._entity_subscriptions[entity_type].append(subscription_id)
        
        # If no specific filters, add to global subscriptions
        if not event_types and not entity_types and not event_filter:
            self._global_subscriptions.append(subscription_id)
        
        self.metrics.record_subscription()
        
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Remove subscription"""
        if subscription_id not in self._subscriptions:
            return False
        
        subscription = self._subscriptions[subscription_id]
        
        # Remove from all indexes
        for event_type_subs in self._type_subscriptions.values():
            if subscription_id in event_type_subs:
                event_type_subs.remove(subscription_id)
        
        for entity_type_subs in self._entity_subscriptions.values():
            if subscription_id in entity_type_subs:
                entity_type_subs.remove(subscription_id)
        
        if subscription_id in self._global_subscriptions:
            self._global_subscriptions.remove(subscription_id)
        
        # Remove subscription
        del self._subscriptions[subscription_id]
        
        return True
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        metrics = self.metrics.get_summary()
        
        # Add subscription details
        metrics.update({
            "active_subscriptions": len(self._subscriptions),
            "type_based_subscriptions": len(self._type_subscriptions),
            "entity_based_subscriptions": len(self._entity_subscriptions),
            "global_subscriptions": len(self._global_subscriptions)
        })
        
        return metrics
    
    async def shutdown(self):
        """Shutdown event bus gracefully"""
        self._shutdown_event.set()
        
        # Wait for any ongoing deliveries to complete
        # This is a simple implementation - in production you might want timeouts
        while self._semaphore.locked():
            await asyncio.sleep(0.1)
        
        # Clear all subscriptions
        self._subscriptions.clear()
        self._type_subscriptions.clear()
        self._entity_subscriptions.clear()
        self._global_subscriptions.clear()
    
    def _find_matching_subscriptions(self, event: DomainEvent) -> Set[str]:
        """Find all subscriptions that should receive this event"""
        matching = set()
        
        # Global subscriptions get all events
        matching.update(self._global_subscriptions)
        
        # Event type based subscriptions
        if event.event_type in self._type_subscriptions:
            matching.update(self._type_subscriptions[event.event_type])
        
        # Entity type based subscriptions
        if event.entity_type in self._entity_subscriptions:
            matching.update(self._entity_subscriptions[event.entity_type])
        
        # Filter by custom filters
        filtered = set()
        for sub_id in matching:
            if sub_id in self._subscriptions:
                subscription = self._subscriptions[sub_id]
                if subscription.should_handle(event):
                    filtered.add(sub_id)
        
        return filtered
    
    async def _deliver_to_subscription(self, subscription: Subscription, event: DomainEvent):
        """Deliver event to a single subscription with error isolation"""
        async with self._semaphore:
            try:
                await subscription.handle_event(event)
            except Exception as e:
                # Isolate errors - one bad handler shouldn't break others
                self.metrics.record_handler_error()
                # In production, you might want to log this
                pass

# Convenience functions for common patterns
async def create_event_bus(bus_type: str = "in_process", **config) -> EventBus:
    """Factory function for creating event buses"""
    if bus_type == "in_process":
        return InProcessEventBus(
            max_concurrent_handlers=config.get("max_concurrent_handlers", 100)
        )
    else:
        raise ValueError(f"Unknown event bus type: {bus_type}")

# Common event filters
class EventFilters:
    """Pre-built event filters for common patterns"""
    
    @staticmethod
    def by_entity_type(entity_type: str) -> EventFilter:
        """Filter events by entity type"""
        return lambda event: event.entity_type == entity_type
    
    @staticmethod
    def by_event_type(event_type: EventType) -> EventFilter:
        """Filter events by event type"""
        return lambda event: event.event_type == event_type
    
    @staticmethod
    def by_user(user_id: str) -> EventFilter:
        """Filter events by user ID"""
        return lambda event: event.user_id == user_id
    
    @staticmethod
    def by_entity_id(entity_id: str) -> EventFilter:
        """Filter events by specific entity ID"""
        return lambda event: event.entity_id == entity_id
    
    @staticmethod
    def combine_and(*filters: EventFilter) -> EventFilter:
        """Combine filters with AND logic"""
        def combined_filter(event: DomainEvent) -> bool:
            return all(f(event) for f in filters)
        return combined_filter
    
    @staticmethod
    def combine_or(*filters: EventFilter) -> EventFilter:
        """Combine filters with OR logic"""
        def combined_filter(event: DomainEvent) -> bool:
            return any(f(event) for f in filters)
        return combined_filter

# Export main components
__all__ = [
    "EventBus", "InProcessEventBus", "EventBusMetrics", "Subscription",
    "EventHandler", "EventFilter", "EventFilters", "create_event_bus",
    "EventBusError", "SubscriptionError", "PublishingError"
]