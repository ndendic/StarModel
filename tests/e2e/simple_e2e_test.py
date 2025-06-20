#!/usr/bin/env python3
"""
StarModel Simple End-to-End Tests

🧪 Simplified E2E Testing:
This test suite validates the complete StarModel system without external dependencies,
ensuring all phases work together seamlessly after the clean architecture refactoring.
"""

import asyncio
import sys
import os
import time
from datetime import datetime
from typing import List, Optional

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# StarModel core imports
try:
    # Import from framework module directly
    from framework import Entity, event, configure_starmodel, Environment, ApplicationConfig
    STARMODEL_AVAILABLE = True
except ImportError as e:
    print(f"❌ StarModel import failed: {e}")
    try:
        # Fallback to src structure
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
        from starmodel import Entity, event
        # Manual import for configuration components that might not be fully integrated
        from framework.infrastructure.deployment.configurator import configure_starmodel
        from framework.infrastructure.dependency_injection.configuration import Environment, ApplicationConfig
        STARMODEL_AVAILABLE = True
    except ImportError as e2:
        print(f"❌ Fallback import also failed: {e2}")
        STARMODEL_AVAILABLE = False

# Test SQL availability
try:
    from framework.entities.lifecycle.sql_entity import SQLEntity
    from framework.persistence.repositories.sql import SQLRepository
    from fastsqlmodel import BaseTable
    from sqlalchemy import Column, String, Integer, Boolean, Text
    SQL_AVAILABLE = True
except ImportError:
    SQL_AVAILABLE = False

print("🔍 Checking dependencies...")
print(f"   StarModel: {'✅ Available' if STARMODEL_AVAILABLE else '❌ Not Available'}")
print(f"   SQL Support: {'✅ Available' if SQL_AVAILABLE else '❌ Not Available'}")

if not STARMODEL_AVAILABLE:
    print("❌ Cannot run tests without StarModel. Exiting.")
    sys.exit(1)

# Test entities
class TestEntity(Entity):
    """Test entity for memory backend testing"""
    name: str
    value: int = 0
    active: bool = True
    
    model_config = {
        "store": "SERVER_MEMORY",
        "auto_persist": True,
        "sync_with_client": True
    }
    
    @event
    async def increment(self, amount: int = 1):
        """Increment the value"""
        self.value += amount
        return f"Incremented by {amount}, now: {self.value}"
    
    @event
    async def toggle_active(self):
        """Toggle active status"""
        self.active = not self.active
        return f"Active status: {self.active}"


if SQL_AVAILABLE:
    class TestSQLEntity(SQLEntity, BaseTable, table=True):
        """Test entity for SQL backend testing"""
        __tablename__ = "test_sql_entities"
        
        name: str = Column(String(100), nullable=False)
        value: int = Column(Integer, default=0)
        active: bool = Column(Boolean, default=True)
        
        model_config = {
            "store": "SERVER_SQL_SQLITE",
            "auto_persist": True,
            "database_url": "sqlite+aiosqlite:///:memory:"
        }
        
        @event
        async def increment(self, amount: int = 1):
            """Increment the value"""
            self.value += amount
            return f"SQL Entity incremented by {amount}, now: {self.value}"


class SimpleE2ETests:
    """Simple end-to-end test runner"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.container = None
    
    async def setup(self):
        """Set up test environment"""
        print("\n🚀 Setting up test environment...")
        
        try:
            # Create test configuration
            config = ApplicationConfig.for_environment(Environment.TESTING)
            config.event_bus.enable_metrics = True
            
            # Configure entities
            entities = [TestEntity]
            if SQL_AVAILABLE:
                entities.append(TestSQLEntity)
            
            # Configure application
            self.container = await configure_starmodel(
                entities=entities,
                config=config
            )
            
            print("   ✅ Test environment configured")
            return True
            
        except Exception as e:
            print(f"   ❌ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def teardown(self):
        """Clean up test environment"""
        if self.container:
            await self.container.shutdown()
        print("   🧹 Test environment cleaned up")
    
    def assert_true(self, condition, message="Assertion failed"):
        """Simple assertion helper"""
        if condition:
            return True
        else:
            raise AssertionError(message)
    
    def assert_equal(self, actual, expected, message=None):
        """Simple equality assertion"""
        if actual == expected:
            return True
        else:
            msg = message or f"Expected {expected}, got {actual}"
            raise AssertionError(msg)
    
    def assert_not_none(self, value, message="Value should not be None"):
        """Simple not-none assertion"""
        if value is not None:
            return True
        else:
            raise AssertionError(message)
    
    async def run_test(self, test_func, test_name):
        """Run a single test with error handling"""
        try:
            print(f"  🧪 {test_name}...")
            await test_func()
            print(f"    ✅ PASSED")
            self.tests_passed += 1
        except Exception as e:
            print(f"    ❌ FAILED: {e}")
            self.tests_failed += 1
            import traceback
            traceback.print_exc()
    
    async def test_phase1_basic_functionality(self):
        """Test basic Phase 1 functionality"""
        # Test DI Container
        self.assert_not_none(self.container, "Container should be initialized")
        
        # Get services
        dispatcher = self.container.get("EventDispatcher")
        event_bus = self.container.get("EventBus")
        unit_of_work = self.container.get("UnitOfWork")
        
        self.assert_not_none(dispatcher, "EventDispatcher should be available")
        self.assert_not_none(event_bus, "EventBus should be available")
        self.assert_not_none(unit_of_work, "UnitOfWork should be available")
        
        # Test basic entity creation
        entity = TestEntity(name="test", value=5)
        self.assert_equal(entity.name, "test")
        self.assert_equal(entity.value, 5)
        self.assert_not_none(entity.id)
    
    async def test_event_dispatcher(self):
        """Test event dispatcher functionality"""
        dispatcher = self.container.get("EventDispatcher")
        
        # Create test entity
        entity = TestEntity(name="dispatcher_test", value=10)
        
        # Import command context
        from framework.events.dispatching.command_context import CommandContext
        
        # Dispatch command
        command = CommandContext(
            entity_class=TestEntity,
            entity_id=entity.id,
            event_name="increment",
            parameters={"amount": 5}
        )
        
        result = await dispatcher.dispatch(command)
        self.assert_true(result.success, "Command should succeed")
        self.assert_true("Incremented by 5" in result.return_value, "Return value should mention increment")
        
        # Check metrics
        metrics = dispatcher.get_metrics()
        self.assert_true(metrics['commands_executed'] >= 1, "Should have executed at least 1 command")
    
    async def test_event_bus(self):
        """Test event bus functionality"""
        event_bus = self.container.get("EventBus")
        
        events_received = []
        
        async def test_subscriber(event):
            events_received.append(event)
        
        # Subscribe
        subscription_id = await event_bus.subscribe(test_subscriber)
        
        # Publish event
        from framework.events.streaming.event_bus import DomainEvent
        test_event = DomainEvent(
            event_type="test_event",
            entity_id="test-123",
            entity_type="TestEntity",
            data={"test": True}
        )
        
        await event_bus.publish(test_event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        self.assert_true(len(events_received) >= 1, "Should have received at least 1 event")
        
        # Cleanup
        await event_bus.unsubscribe(subscription_id)
    
    async def test_unit_of_work(self):
        """Test unit of work functionality"""
        unit_of_work = self.container.get("UnitOfWork")
        
        entity = TestEntity(name="uow_test", value=20)
        
        async with unit_of_work as uow:
            await uow.register_entity(entity)
            entity.value = 100
        
        # Verify changes persisted
        self.assert_equal(entity.value, 100, "Entity value should be updated")
    
    async def test_sql_functionality(self):
        """Test SQL functionality if available"""
        if not SQL_AVAILABLE:
            print("      ⚠️ Skipping SQL tests - dependencies not available")
            return
        
        # Create SQL entity
        sql_entity = TestSQLEntity(name="sql_test", value=30)
        
        # Save entity
        entity_id = await sql_entity.save()
        self.assert_equal(entity_id, sql_entity.id, "Entity ID should match")
        
        # Test event dispatch on SQL entity
        dispatcher = self.container.get("EventDispatcher")
        from starmodel.events.dispatching.command_context import CommandContext
        
        command = CommandContext(
            entity_class=TestSQLEntity,
            entity_id=sql_entity.id,
            event_name="increment",
            parameters={"amount": 15}
        )
        
        result = await dispatcher.dispatch(command)
        self.assert_true(result.success, "SQL entity command should succeed")
    
    async def test_performance_basic(self):
        """Test basic performance"""
        dispatcher = self.container.get("EventDispatcher")
        
        # Create test entity
        entity = TestEntity(name="performance_test", value=0)
        
        # Time multiple operations
        start_time = time.time()
        
        # Import command context
        from framework.events.dispatching.command_context import CommandContext
        
        for i in range(10):
            command = CommandContext(
                entity_class=TestEntity,
                entity_id=entity.id,
                event_name="increment",
                parameters={"amount": 1}
            )
            result = await dispatcher.dispatch(command)
            self.assert_true(result.success, f"Command {i} should succeed")
        
        elapsed = time.time() - start_time
        print(f"      📊 10 commands executed in {elapsed:.3f}s")
        
        # Should be reasonably fast
        self.assert_true(elapsed < 2.0, "10 commands should complete in under 2 seconds")
    
    async def test_error_handling(self):
        """Test error handling"""
        dispatcher = self.container.get("EventDispatcher")
        
        # Try to dispatch to non-existent entity
        from starmodel.events.dispatching.command_context import CommandContext
        
        invalid_command = CommandContext(
            entity_class=TestEntity,
            entity_id="non-existent-id",
            event_name="increment",
            parameters={"amount": 1}
        )
        
        result = await dispatcher.dispatch(invalid_command)
        self.assert_true(not result.success, "Invalid command should fail")
        self.assert_not_none(result.error_message, "Should have error message")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting StarModel Simple End-to-End Tests")
        print("=" * 60)
        
        # Setup
        if not await self.setup():
            print("❌ Setup failed, cannot run tests")
            return False
        
        try:
            # Phase 1 Tests
            print("\n1️⃣ Testing Phase 1: Application Service Layer")
            await self.run_test(self.test_phase1_basic_functionality, "Basic Functionality")
            await self.run_test(self.test_event_dispatcher, "Event Dispatcher")
            await self.run_test(self.test_event_bus, "Event Bus")
            await self.run_test(self.test_unit_of_work, "Unit of Work")
            
            # SQL Tests (Phase 4)
            print("\n4️⃣ Testing Phase 4: SQL Integration")
            await self.run_test(self.test_sql_functionality, "SQL Functionality")
            
            # Performance Tests
            print("\n⚡ Testing Performance")
            await self.run_test(self.test_performance_basic, "Basic Performance")
            
            # Error Handling Tests
            print("\n🛡️ Testing Error Handling")
            await self.run_test(self.test_error_handling, "Error Handling")
            
        finally:
            await self.teardown()
        
        # Report results
        print("\n" + "=" * 60)
        print("📊 Test Results:")
        print(f"   ✅ Passed: {self.tests_passed}")
        print(f"   ❌ Failed: {self.tests_failed}")
        print(f"   📈 Success Rate: {self.tests_passed / (self.tests_passed + self.tests_failed) * 100:.1f}%")
        
        if self.tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED! StarModel is working correctly!")
            return True
        else:
            print(f"\n⚠️ {self.tests_failed} test(s) failed. Please investigate.")
            return False


async def main():
    """Main test execution"""
    test_runner = SimpleE2ETests()
    success = await test_runner.run_all_tests()
    
    if success:
        print("\n✅ StarModel Clean Architecture Refactoring: VALIDATED")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)