#!/usr/bin/env python3
"""
StarModel Clean Architecture Demo

This example demonstrates the complete Phase 1 implementation with:
- Clean architecture separation (Domain, Application, Infrastructure)
- Event Dispatcher with command processing
- Unit of Work for transaction coordination
- Event Bus for domain event publishing
- Dependency Injection container
- Configuration-driven setup
"""

import asyncio
from datetime import datetime
from typing import List, Optional

# Import StarModel with clean architecture
from starmodel import Entity, event, configure_starmodel, Environment, ApplicationConfig


# 🎯 DOMAIN LAYER - Pure business logic
class BlogPost(Entity):
    """Blog post entity with domain behavior"""
    title: str
    content: str
    published: bool = False
    publish_date: Optional[datetime] = None
    view_count: int = 0
    tags: List[str] = []
    
    # Configure this entity to use memory persistence
    model_config = {
        "store": "SERVER_MEMORY",
        "auto_persist": True,
        "sync_with_client": True
    }
    
    @event
    async def publish(self):
        """Publish this blog post"""
        if not self.published:
            self.published = True
            self.publish_date = datetime.now()
            print(f"📄 Blog post '{self.title}' published!")
    
    @event  
    async def add_view(self):
        """Track a view of this post"""
        self.view_count += 1
        print(f"👁️  View count for '{self.title}': {self.view_count}")
    
    @event
    async def add_tag(self, tag: str):
        """Add a tag to this post"""
        if tag not in self.tags:
            self.tags.append(tag)
            print(f"🏷️  Added tag '{tag}' to '{self.title}'")

class Counter(Entity):
    """Simple counter entity for demonstration"""
    count: int = 0
    increment_history: List[datetime] = []
    
    model_config = {
        "store": "SERVER_MEMORY",
        "auto_persist": True
    }
    
    @event
    async def increment(self, amount: int = 1):
        """Increment the counter"""
        self.count += amount
        self.increment_history.append(datetime.now())
        print(f"🔢 Counter incremented by {amount}, now: {self.count}")
    
    @event
    async def reset(self):
        """Reset the counter"""
        old_count = self.count
        self.count = 0
        self.increment_history.clear()
        print(f"🔄 Counter reset from {old_count} to 0")


# 📋 APPLICATION ORCHESTRATION
async def demonstrate_clean_architecture():
    """Demonstrate the complete clean architecture implementation"""
    
    print("🚀 StarModel Clean Architecture Demo")
    print("=" * 50)
    
    # 1. Configure application with clean architecture
    print("\n1️⃣  Configuring StarModel with Clean Architecture...")
    
    # Create development configuration
    config = ApplicationConfig.for_environment(Environment.DEVELOPMENT)
    config.event_bus.enable_metrics = True
    
    # Configure the application
    container = await configure_starmodel(
        entities=[BlogPost, Counter],
        config=config
    )
    
    print("   ✅ Dependency injection container configured")
    print("   ✅ Event dispatcher ready")
    print("   ✅ Event bus configured")
    print("   ✅ Unit of Work ready")
    print("   ✅ Persistence layer configured")
    
    # 2. Get application services from DI container
    print("\n2️⃣  Getting Application Services...")
    
    dispatcher = container.get("EventDispatcher")
    event_bus = container.get("EventBus")
    unit_of_work = container.get("UnitOfWork")
    
    print(f"   📨 Event Dispatcher: {type(dispatcher).__name__}")
    print(f"   🚌 Event Bus: {type(event_bus).__name__}")
    print(f"   💾 Unit of Work: {type(unit_of_work).__name__}")
    
    # 3. Demonstrate domain entities with events
    print("\n3️⃣  Creating and Using Domain Entities...")
    
    # Create entities
    blog_post = BlogPost(
        title="Clean Architecture in Python",
        content="This post explains clean architecture principles..."
    )
    
    counter = Counter()
    
    print(f"   📄 Created blog post: '{blog_post.title}'")
    print(f"   🔢 Created counter with value: {counter.count}")
    
    # 4. Execute commands through the dispatcher
    print("\n4️⃣  Executing Commands through Event Dispatcher...")
    
    from starmodel.events.dispatching.command_context import CommandContext
    
    # Execute blog post commands
    await dispatcher.dispatch(CommandContext(
        entity_class=BlogPost,
        entity_id=blog_post.id,
        event_name="add_tag",
        parameters={"tag": "architecture"}
    ))
    
    await dispatcher.dispatch(CommandContext(
        entity_class=BlogPost,
        entity_id=blog_post.id,
        event_name="publish",
        parameters={}
    ))
    
    await dispatcher.dispatch(CommandContext(
        entity_class=BlogPost,
        entity_id=blog_post.id,
        event_name="add_view",
        parameters={}
    ))
    
    # Execute counter commands
    await dispatcher.dispatch(CommandContext(
        entity_class=Counter,
        entity_id=counter.id,
        event_name="increment",
        parameters={"amount": 5}
    ))
    
    await dispatcher.dispatch(CommandContext(
        entity_class=Counter,
        entity_id=counter.id,
        event_name="increment",
        parameters={"amount": 3}
    ))
    
    # 5. Demonstrate Unit of Work transaction coordination
    print("\n5️⃣  Demonstrating Unit of Work Transactions...")
    
    async with unit_of_work as uow:
        # Register entities for persistence
        await uow.register_entity(blog_post)
        await uow.register_entity(counter)
        
        # Execute additional changes
        blog_post.content += "\n\nThis content was added in a transaction!"
        counter.count += 10
        
        print("   💾 Entities registered in Unit of Work")
        print("   🔄 Changes will be committed atomically")
        # Commit happens automatically on successful exit
    
    print("   ✅ Transaction committed successfully")
    
    # 6. Check event bus metrics
    print("\n6️⃣  Event Bus Metrics...")
    
    metrics = await event_bus.get_metrics()
    print(f"   📊 Events published: {metrics['events_published']}")
    print(f"   📨 Events delivered: {metrics['events_delivered']}")
    print(f"   🔌 Active subscriptions: {metrics['active_subscriptions']}")
    
    # 7. Check dispatcher metrics
    print("\n7️⃣  Event Dispatcher Metrics...")
    
    dispatcher_metrics = dispatcher.get_metrics()
    print(f"   ⚡ Commands executed: {dispatcher_metrics['commands_executed']}")
    print(f"   ✅ Commands succeeded: {dispatcher_metrics['commands_succeeded']}")
    print(f"   📈 Success rate: {dispatcher_metrics['success_rate']:.1f}%")
    print(f"   ⏱️  Average execution time: {dispatcher_metrics['average_execution_time_ms']:.2f}ms")
    
    # 8. Show final entity states
    print("\n8️⃣  Final Entity States...")
    
    print(f"   📄 Blog Post: '{blog_post.title}'")
    print(f"      - Published: {blog_post.published}")
    print(f"      - Views: {blog_post.view_count}")
    print(f"      - Tags: {blog_post.tags}")
    print(f"      - Publish date: {blog_post.publish_date}")
    
    print(f"   🔢 Counter: {counter.count}")
    print(f"      - Increment history: {len(counter.increment_history)} events")
    
    # 9. Demonstrate reactive signals
    print("\n9️⃣  Reactive Signals for UI Binding...")
    
    print("   🔄 Generated signals for BlogPost:")
    print(f"      - Title signal: {BlogPost.title_signal}")
    print(f"      - Published signal: {BlogPost.published_signal}")
    print(f"      - View count signal: {BlogPost.view_count_signal}")
    
    print("   🔄 Generated signals for Counter:")
    print(f"      - Count signal: {Counter.count_signal}")
    
    # 10. Cleanup
    print("\n🔟 Cleanup...")
    
    await container.shutdown()
    print("   ✅ Container shut down gracefully")
    
    print("\n" + "=" * 50)
    print("🎉 Clean Architecture Demo Complete!")
    print("\n✅ Successfully demonstrated:")
    print("   - Clean architecture separation")
    print("   - Event-driven command processing")
    print("   - Transaction coordination")
    print("   - Domain event publishing")
    print("   - Dependency injection")
    print("   - Configuration-driven setup")
    print("   - Reactive signal generation")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_clean_architecture())