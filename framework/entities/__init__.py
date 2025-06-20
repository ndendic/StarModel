"""
Entities - The Heart of StarModel

🎯 Entity-Centric Design Philosophy:
Entities are domain objects that contain both data and behavior.
They are the primary building blocks of StarModel applications.

Structure:
- lifecycle/: Entity creation, updates, deletion, and state management
- behavior/: Business logic, @event methods, and domain rules
- composition/: Entity relationships, aggregates, and value objects  
- validation/: Business constraints and validation rules

Example:
    from starmodel.entities import Entity, event
    
    class BlogPost(Entity):
        title: str
        content: str
        published: bool = False
        
        @event
        async def publish(self):
            self.published = True
"""

# Primary exports - what developers use
try:
    from .lifecycle.entity import Entity
    from .behavior.events import event, EventCapable
    from .validation.constraints import validate_entity
    from .composition.relationships import related_to, has_many
except ImportError:
    # During migration, use placeholders
    Entity = None
    event = None
    EventCapable = None
    validate_entity = None
    related_to = None
    has_many = None

# Backward compatibility during migration
try:
    from .lifecycle.entity import Entity as CoreEntity
    from .behavior.events import event as core_event
except ImportError:
    CoreEntity = Entity
    core_event = event

__all__ = [
    "Entity", "event", "EventCapable", "validate_entity",
    "related_to", "has_many",
    # Legacy compatibility
    "CoreEntity", "core_event"
]