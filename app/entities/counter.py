"""
Counter Entity

Domain logic for a persistent, globally-shared counter with real-time synchronization.
"""

import asyncio
from starmodel import Entity, event, EntityStore, memory_persistence

class CounterEntity(Entity): 
    """Enhanced counter with persistence and real-time sync."""
    model_config = {
        "arbitrary_types_allowed": True,
        "starmodel_store": EntityStore.SERVER_MEMORY,
        "starmodel_auto_persist": True,
        "starmodel_persistence_backend": memory_persistence,
        "starmodel_ttl": 10,
    }
    
    count: int = 0
    last_updated_by: str = ""
    update_count: int = 0
    id: str = "global_counter"
    
    @event(method="post")
    async def increment(self, amount: int = 1, user: str = "Anonymous"):      
        self.update_count += 1
        for i in range(amount):
            self.count += 1
            self.last_updated_by = user
            await asyncio.sleep(i/1000)
            from fasthtml.common import Div
            yield Div(f"Counter incremented by {i+1} by {user}",id="message", cls="font-mono text-sm text-green-600")
    
    @event(method="post")
    async def decrement(self, amount: int = 1, user: str = "Anonymous"):
        self.update_count += 1
        for i in range(amount):
            self.count -= 1
            self.last_updated_by = user
            await asyncio.sleep(i/1000)
            from fasthtml.common import Div
            yield Div(f"Counter decremented by {i+1} by {user}",id="message", cls="font-mono text-sm text-red-600")
        
    
    @event(method="post")
    async def reset(self, user: str = "Anonymous"):
        self.update_count += 1
        for i in range(abs(self.count)):
            if self.count > 0: self.count -= 1 
            else: self.count += 1
            self.last_updated_by = user
            await asyncio.sleep(i/1000)
            from fasthtml.common import Div
            yield Div(f"Counter reset by {user}",id="message", cls="font-mono text-sm text-blue-600")