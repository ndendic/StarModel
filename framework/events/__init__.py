"""
Events - Event-Driven Interactions

🚀 Command-Based Architecture:
Events represent user actions and system commands that trigger entity behavior.
This module handles the complete event lifecycle from command to response.

Structure:
- commands/: Event definitions, @event decorator, and command metadata
- handlers/: Event processing logic and middleware pipeline
- dispatching/: Command routing, execution, and coordination
- streaming/: Event buses, pub/sub messaging, and event streams

Example:
    from starmodel.events import event, EventDispatcher
    
    class ShoppingCart(Entity):
        items: List[str] = []
        
        @event(description="Add item to cart")
        async def add_item(self, item: str, quantity: int = 1):
            self.items.append(f"{quantity}x {item}")
"""

# Primary exports
try:
    from .commands.event import event, EventMetadata
    from .dispatching.dispatcher import EventDispatcher, CommandContext
    from .streaming.event_bus import EventBus, InProcessEventBus
    from .handlers.middleware import EventMiddleware
except ImportError:
    # Placeholders during migration
    event = None
    EventMetadata = None
    EventDispatcher = None
    CommandContext = None
    EventBus = None
    InProcessEventBus = None
    EventMiddleware = None

__all__ = [
    "event", "EventMetadata", "EventDispatcher", "CommandContext",
    "EventBus", "InProcessEventBus", "EventMiddleware"
]