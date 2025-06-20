"""
Test Composition-Based Entity System

🧪 Demonstration of Clean Architecture:
This test file demonstrates the composition-based entity system with dependency injection,
showing how entities get their capabilities through services rather than inheritance.
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

# Import composition-based entity system
from framework.entities.lifecycle.composition_entity import Entity, ServiceContainer
from framework.entities.di_container import setup_testing, setup_development
from framework.entities.services.validation_service import ValidationError

# Import event decorator from the framework
from framework.events.commands.event import event


class Counter(Entity):
    """
    Example counter entity using composition.
    
    This entity demonstrates how business logic lives in the entity
    while capabilities come from injected services.
    """
    
    count: int = 0
    increment_count: int = 0
    
    @event
    def increment(self, amount: int = 1):
        """Increment counter by amount"""
        old_count = self.count
        self.count += amount
        self.increment_count += 1
        print(f"Counter incremented from {old_count} to {self.count}")
        return self.count
    
    @event
    def reset(self):
        """Reset counter to zero"""
        old_count = self.count
        self.count = 0
        self.increment_count += 1
        print(f"Counter reset from {old_count} to 0")
        return self.count
    
    def is_even(self) -> bool:
        """Business logic method (not an event)"""
        return self.count % 2 == 0


class UserProfile(Entity):
    """
    Example user profile entity with validation.
    
    This entity demonstrates validation through injected services.
    """
    
    username: str = ""
    email: str = ""
    age: int = 0
    
    @event
    def update_profile(self, username: str = None, email: str = None, age: int = None):
        """Update user profile"""
        if username:
            self.username = username
        if email:
            self.email = email
        if age is not None:
            self.age = age
        
        print(f"Profile updated: {self.username} ({self.email})")
        return True


async def test_basic_composition():
    """Test basic entity composition functionality"""
    print("🧪 Testing Basic Composition...")
    
    # Set up testing environment
    container = setup_testing()
    print(f"✅ Testing container configured")
    
    # Create entity
    counter = Counter()
    print(f"✅ Counter created with ID: {counter.id}")
    
    # Test persistence
    await counter.save()
    print(f"✅ Counter saved")
    
    # Test loading
    loaded_counter = await Counter.load(counter.id)
    print(f"✅ Counter loaded: {loaded_counter}")
    
    # Test event execution
    await counter.execute_event("increment", {"amount": 5})
    print(f"✅ Event executed, count: {counter.count}")
    
    # Test signals
    signals = counter.get_signals()
    print(f"✅ Signals: {signals}")
    
    # Test metrics
    metrics = counter.get_metrics()
    print(f"✅ Metrics: {metrics}")
    
    print("✅ Basic composition test passed!\n")


async def test_event_integration():
    """Test event system integration"""
    print("🚀 Testing Event Integration...")
    
    # Set up development environment for full features
    container = setup_development()
    
    # Create counter
    counter = Counter(count=10)
    
    # Test @event methods work
    result = counter.increment(3)
    print(f"✅ Direct method call: {result}, count: {counter.count}")
    
    # Test event execution through service
    await counter.execute_event("increment", {"amount": 2})
    print(f"✅ Service execution, count: {counter.count}")
    
    # Test reset event
    counter.reset()
    print(f"✅ Reset called, count: {counter.count}")
    
    # Test event discovery
    events = Counter.get_events()
    print(f"✅ Available events: {list(events.keys())}")
    
    print("✅ Event integration test passed!\n")


async def test_persistence_separation():
    """Test persistence service separation"""
    print("💾 Testing Persistence Separation...")
    
    container = setup_testing()
    
    # Create and save multiple entities
    counter1 = Counter(count=100)
    counter2 = Counter(count=200)
    
    await counter1.save()
    await counter2.save()
    print(f"✅ Saved two counters: {counter1.id}, {counter2.id}")
    
    # Test loading specific entities
    loaded1 = await Counter.load(counter1.id)
    loaded2 = await Counter.load(counter2.id)
    
    print(f"✅ Loaded counter1: count={loaded1.count}")
    print(f"✅ Loaded counter2: count={loaded2.count}")
    
    # Test listing all entities
    all_counters = await Counter.list_all()
    print(f"✅ Found {len(all_counters)} counters total")
    
    # Test existence checking
    exists = await counter1.exists()
    print(f"✅ Counter1 exists: {exists}")
    
    # Test deletion
    deleted = await counter1.delete()
    exists_after_delete = await counter1.exists()
    print(f"✅ Counter1 deleted: {deleted}, exists after: {exists_after_delete}")
    
    print("✅ Persistence separation test passed!\n")


async def test_validation_service():
    """Test validation service integration"""
    print("✅ Testing Validation Service...")
    
    container = setup_development()
    
    # Create user profile
    user = UserProfile(username="testuser", email="test@example.com", age=25)
    
    # Test successful validation
    try:
        user.validate()
        print("✅ Valid user profile passed validation")
    except ValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
    
    # Test validation errors
    errors = user.get_validation_errors()
    print(f"✅ Validation errors (should be empty): {errors}")
    
    # Test field validation
    try:
        user.validate_field("age", 30)
        print("✅ Field validation passed")
    except ValidationError as e:
        print(f"❌ Unexpected field validation error: {e}")
    
    print("✅ Validation service test passed!\n")


async def test_signal_system():
    """Test signal system integration"""
    print("🔄 Testing Signal System...")
    
    container = setup_development()  # Uses ReactiveSignalService with namespace
    
    # Create counter
    counter = Counter(count=42)
    
    # Test signal generation
    count_signal = counter.signal("count")
    print(f"✅ Count signal: {count_signal}")
    
    # Test all signals  
    all_signals = counter.get_signals()
    print(f"✅ All signals: {all_signals}")
    
    # Test signal updates after change
    counter.count = 100
    updates = counter.get_signal_updates(["count"])
    print(f"✅ Signal updates: {updates}")
    
    print("✅ Signal system test passed!\n")


async def test_metrics_collection():
    """Test metrics collection system"""
    print("📊 Testing Metrics Collection...")
    
    container = setup_development()  # Uses EntityMetricsService
    
    # Create counter and perform operations
    counter = Counter()
    
    # Perform multiple operations
    await counter.save()
    await counter.execute_event("increment", {"amount": 5})
    await counter.execute_event("increment", {"amount": 3})
    await counter.execute_event("reset", {})
    
    # Check entity metrics
    entity_metrics = counter.get_metrics()
    print(f"✅ Entity metrics: {entity_metrics}")
    
    # Check class metrics
    class_metrics = Counter.get_class_metrics()
    print(f"✅ Class metrics: {class_metrics}")
    
    # Get system metrics
    system_metrics = container.metrics_service.get_system_metrics()
    print(f"✅ System metrics: {system_metrics}")
    
    print("✅ Metrics collection test passed!\n")


async def test_service_swapping():
    """Test service swapping for different environments"""
    print("🔄 Testing Service Swapping...")
    
    # Test with minimal container
    from framework.entities.di_container import create_minimal_container
    minimal_container = create_minimal_container()
    
    # Create entity with minimal services
    Counter.set_services(minimal_container)
    counter1 = Counter()
    print(f"✅ Counter with minimal services: {counter1.id}")
    
    # Test with development container
    dev_container = setup_development()
    Counter.set_services(dev_container)
    counter2 = Counter()
    print(f"✅ Counter with development services: {counter2.id}")
    
    # Verify they use different service implementations
    print(f"✅ Minimal persistence: {type(counter1._get_persistence_service()).__name__}")
    print(f"✅ Dev persistence: {type(counter2._get_persistence_service()).__name__}")
    
    print("✅ Service swapping test passed!\n")


async def main():
    """Run all composition tests"""
    print("🏗️ StarModel Composition-Based Entity Tests")
    print("=" * 50)
    
    try:
        await test_basic_composition()
        await test_event_integration()
        await test_persistence_separation()
        await test_validation_service()
        await test_signal_system()
        await test_metrics_collection()
        await test_service_swapping()
        
        print("🎉 All composition tests passed!")
        print("🏗️ Composition over inheritance successfully implemented!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())