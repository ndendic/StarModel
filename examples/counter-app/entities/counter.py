"""
Counter Entity - Simple Interactive Counter

This demonstrates StarModel's core capabilities:
- Entity with state (count)
- Interactive events (increment, decrement, reset)
- Real-time UI updates
- Persistent state
"""

# Use the new screaming architecture imports once migration is complete
# For now, this serves as a template for the target structure

# from starmodel.entities import Entity, event

class Counter:
    """
    A simple counter that demonstrates entity-event patterns
    
    This is a placeholder during Phase 0 migration.
    Will become a proper Entity once core files are migrated.
    """
    
    def __init__(self):
        self.count = 0
        self.increment_count = 0
    
    def increment(self, amount: int = 1):
        """Increment the counter"""
        self.count += amount
        self.increment_count += 1
    
    def decrement(self, amount: int = 1):
        """Decrement the counter"""
        self.count -= amount
    
    def reset(self):
        """Reset counter to zero"""
        self.count = 0

# TODO: Convert to StarModel Entity after migration
# class Counter(Entity):
#     """A simple counter that demonstrates entity-event patterns"""
#     
#     count: int = 0
#     increment_count: int = 0
#     
#     model_config = {
#         "store": "memory",  # Use memory backend for demo
#         "realtime": True,   # Enable real-time updates
#     }
#     
#     @event(description="Increase counter by specified amount")
#     async def increment(self, amount: int = 1):
#         """Increment the counter"""
#         self.count += amount
#         self.increment_count += 1
#     
#     @event(description="Decrease counter by specified amount")
#     async def decrement(self, amount: int = 1):
#         """Decrement the counter"""
#         self.count -= amount
#     
#     @event(description="Reset counter to zero")
#     async def reset(self):
#         """Reset counter to zero"""
#         self.count = 0