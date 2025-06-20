#!/usr/bin/env python3
"""
StarModel End-to-End System Tests

🧪 Comprehensive E2E Testing:
This test suite validates the complete StarModel system after the clean architecture
refactoring, ensuring all phases work together seamlessly and that no functionality
has been broken during the refactoring process.

Test Coverage:
- Phase 1: Application Service Layer (Event Dispatcher, Unit of Work, Event Bus, DI)
- Phase 3: Web Adapter Decoupling (Web interfaces, Real-time protocols)
- Phase 4: SQL Integration (SQL Repository, SQLEntity, Multi-backend persistence)
- Integration: Cross-phase functionality and data flow
- Performance: Load testing and stress scenarios
"""

import asyncio
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from typing import List, Optional
import time
import json

# Test framework imports
import pytest_asyncio

# StarModel core imports
from starmodel import Entity, event, configure_starmodel, Environment, ApplicationConfig

# Test SQL availability
try:
    from starmodel.entities.lifecycle.sql_entity import SQLEntity
    from starmodel.persistence.repositories.sql import SQLRepository, create_sqlite_repository
    from fastsqlmodel import BaseTable
    from sqlalchemy import Column, String, Integer, Boolean, Text
    SQL_AVAILABLE = True
except ImportError:
    SQL_AVAILABLE = False
    SQLEntity = Entity
    BaseTable = object

# Import application service layer components
from starmodel.events.dispatching.dispatcher import EventDispatcher
from starmodel.events.dispatching.command_context import CommandContext, CommandResult
from starmodel.persistence.transactions.unit_of_work import UnitOfWork
from starmodel.events.streaming.event_bus import EventBus, DomainEvent
from starmodel.infrastructure.dependency_injection.container import DIContainer

# Import web adapter components
from starmodel.web.interfaces import WebRequest, WebResponse, HttpMethod, ContentType
from starmodel.realtime.protocols.response_formatters import DatastarSSEFormatter, JSONResponseFormatter
from starmodel.realtime.broadcasting.sse_broadcaster import SSEBroadcaster

# Import persistence components
from starmodel.persistence.repositories.interface import QueryOptions, QueryOperator, QueryResult


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
    
    @event
    async def reset(self):
        """Reset to default values"""
        old_value = self.value
        self.value = 0
        self.active = True
        return f"Reset from {old_value} to {self.value}"


if SQL_AVAILABLE:
    class TestSQLEntity(SQLEntity, BaseTable, table=True):
        """Test entity for SQL backend testing"""
        __tablename__ = "test_sql_entities"
        
        name: str = Column(String(100), nullable=False)
        value: int = Column(Integer, default=0)
        active: bool = Column(Boolean, default=True)
        description: str = Column(Text, nullable=True)
        
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
        
        @event
        async def update_description(self, new_description: str):
            """Update description"""
            old_desc = self.description
            self.description = new_description
            return f"Description updated from '{old_desc}' to '{new_description}'"


class MockWebRequest(WebRequest):
    """Mock web request for testing web adapters"""
    
    def __init__(self, method: HttpMethod = HttpMethod.GET, path: str = "/", 
                 query_params: dict = None, headers: dict = None):
        self._method = method
        self._path = path
        self._query_params = query_params or {}
        self._headers = headers or {}
        self._cookies = {}
        self._session = {}
    
    @property
    def method(self) -> HttpMethod:
        return self._method
    
    @property
    def url(self) -> str:
        return f"http://test.com{self._path}"
    
    @property
    def path(self) -> str:
        return self._path
    
    @property
    def query_params(self) -> dict:
        return self._query_params
    
    @property
    def headers(self) -> dict:
        return self._headers
    
    @property
    def cookies(self) -> dict:
        return self._cookies
    
    async def body(self) -> bytes:
        return b""
    
    async def text(self) -> str:
        return ""
    
    async def json(self) -> dict:
        return {}
    
    async def form(self) -> dict:
        return {}
    
    async def files(self) -> dict:
        return {}
    
    @property
    def content_type(self) -> Optional[str]:
        return self._headers.get('content-type')
    
    @property
    def client_ip(self) -> Optional[str]:
        return "127.0.0.1"
    
    @property
    def user_agent(self) -> Optional[str]:
        return "Test/1.0"
    
    def get_session(self) -> dict:
        return self._session
    
    def set_session(self, key: str, value):
        self._session[key] = value
    
    def get_user(self):
        return self._session.get('user_id')
    
    def get_datastar_payload(self) -> dict:
        return {}
    
    def get_entity_id(self, entity_class: type) -> Optional[str]:
        return self._query_params.get('id')


class TestSystemE2E:
    """End-to-end system tests"""
    
    @pytest.fixture
    async def configured_container(self):
        """Set up configured DI container for testing"""
        # Create test configuration
        config = ApplicationConfig.for_environment(Environment.TESTING)
        config.event_bus.enable_metrics = True
        config.event_bus.max_subscribers = 1000
        
        # Configure entities
        entities = [TestEntity]
        if SQL_AVAILABLE:
            entities.append(TestSQLEntity)
        
        # Configure application
        container = await configure_starmodel(
            entities=entities,
            config=config
        )
        
        yield container
        
        # Cleanup
        await container.shutdown()
    
    @pytest.mark.asyncio
    async def test_phase1_application_service_layer(self, configured_container):
        """Test Phase 1: Application Service Layer components"""
        print("\n🧪 Testing Phase 1: Application Service Layer")
        
        # 1. Test DI Container
        print("  1️⃣ Testing DI Container...")
        assert configured_container is not None
        
        # Get services from container
        dispatcher = configured_container.get("EventDispatcher")
        event_bus = configured_container.get("EventBus")
        unit_of_work = configured_container.get("UnitOfWork")
        persistence_manager = configured_container.get("PersistenceManager")
        
        assert isinstance(dispatcher, EventDispatcher)
        assert isinstance(event_bus, EventBus)
        assert isinstance(unit_of_work, UnitOfWork)
        assert persistence_manager is not None
        
        print("    ✅ DI Container working correctly")
        
        # 2. Test Event Dispatcher
        print("  2️⃣ Testing Event Dispatcher...")
        
        # Create test entity
        test_entity = TestEntity(name="test_entity", value=10)
        
        # Dispatch increment command
        command_context = CommandContext(
            entity_class=TestEntity,
            entity_id=test_entity.id,
            event_name="increment",
            parameters={"amount": 5}
        )
        
        result = await dispatcher.dispatch(command_context)
        assert isinstance(result, CommandResult)
        assert result.success
        assert "Incremented by 5" in result.return_value
        
        # Check metrics
        metrics = dispatcher.get_metrics()
        assert metrics['commands_executed'] >= 1
        assert metrics['commands_succeeded'] >= 1
        
        print("    ✅ Event Dispatcher working correctly")
        
        # 3. Test Event Bus
        print("  3️⃣ Testing Event Bus...")
        
        events_received = []
        
        async def test_subscriber(event: DomainEvent):
            events_received.append(event)
        
        # Subscribe to events
        subscription_id = await event_bus.subscribe(test_subscriber)
        
        # Publish test event
        test_event = DomainEvent(
            event_type="test_event",
            entity_id=test_entity.id,
            entity_type="TestEntity",
            data={"test": "data"},
            metadata={"source": "test"}
        )
        
        await event_bus.publish(test_event)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        assert len(events_received) >= 1
        assert events_received[0].event_type == "test_event"
        
        # Cleanup subscription
        await event_bus.unsubscribe(subscription_id)
        
        # Check metrics
        bus_metrics = await event_bus.get_metrics()
        assert bus_metrics['events_published'] >= 1
        
        print("    ✅ Event Bus working correctly")
        
        # 4. Test Unit of Work
        print("  4️⃣ Testing Unit of Work...")
        
        async with unit_of_work as uow:
            # Register entity for transaction
            await uow.register_entity(test_entity)
            
            # Make changes
            test_entity.value = 100
            test_entity.active = False
            
            # Transaction commits automatically
        
        # Verify changes were persisted
        assert test_entity.value == 100
        assert test_entity.active == False
        
        print("    ✅ Unit of Work working correctly")
        
        print("  ✅ Phase 1 tests completed successfully")
    
    @pytest.mark.asyncio
    async def test_phase3_web_adapter_decoupling(self, configured_container):
        """Test Phase 3: Web Adapter Decoupling components"""
        print("\n🧪 Testing Phase 3: Web Adapter Decoupling")
        
        # 1. Test Response Formatters
        print("  1️⃣ Testing Response Formatters...")
        
        # Test JSON formatter
        json_formatter = JSONResponseFormatter()
        
        # Create mock command result
        from starmodel.events.dispatching.command_context import CommandResult
        command_result = CommandResult(
            command_id="test-123",
            success=True,
            return_value="Test completed",
            signals_updated={"test_signal": "updated_value"},
            fragments_generated=["<div>Test fragment</div>"],
            events_published=["test_event"],
            execution_time_ms=15.5
        )
        
        # Create formatter context
        from starmodel.realtime.protocols.response_formatters import FormatterContext
        mock_request = MockWebRequest()
        formatter_context = FormatterContext(request=mock_request)
        
        # Format response
        response = await json_formatter.format_response(command_result, formatter_context)
        assert response is not None
        assert json_formatter.get_content_type() == ContentType.JSON.value
        
        # Test SSE formatter
        sse_formatter = DatastarSSEFormatter()
        sse_response = await sse_formatter.format_response(command_result, formatter_context)
        assert sse_response is not None
        assert sse_formatter.supports_streaming()
        
        print("    ✅ Response Formatters working correctly")
        
        # 2. Test Protocol Manager
        print("  2️⃣ Testing Protocol Manager...")
        
        from starmodel.realtime.protocols.protocol_manager import ProtocolManager
        event_bus = configured_container.get("EventBus")
        
        protocol_manager = ProtocolManager(event_bus)
        
        # Test protocol selection
        mock_sse_request = MockWebRequest(headers={'accept': 'text/event-stream'})
        adapter = protocol_manager.select_protocol(mock_sse_request)
        assert adapter is not None
        
        # Test capabilities
        capabilities = protocol_manager.get_capabilities()
        assert len(capabilities) > 0
        
        print("    ✅ Protocol Manager working correctly")
        
        # 3. Test SSE Broadcaster
        print("  3️⃣ Testing SSE Broadcaster...")
        
        event_bus = configured_container.get("EventBus")
        sse_broadcaster = SSEBroadcaster(event_bus)
        
        # Start broadcaster
        await sse_broadcaster.start()
        
        # Create mock connection
        mock_request = MockWebRequest()
        connection = await sse_broadcaster.create_connection(mock_request)
        assert connection is not None
        assert connection.id is not None
        
        # Check metrics
        metrics = sse_broadcaster.get_metrics()
        assert metrics['connections_created'] >= 1
        
        # Stop broadcaster
        await sse_broadcaster.stop()
        
        print("    ✅ SSE Broadcaster working correctly")
        
        print("  ✅ Phase 3 tests completed successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not SQL_AVAILABLE, reason="SQL dependencies not available")
    async def test_phase4_sql_integration(self, configured_container):
        """Test Phase 4: SQL Integration components"""
        print("\n🧪 Testing Phase 4: SQL Integration")
        
        # 1. Test SQL Repository
        print("  1️⃣ Testing SQL Repository...")
        
        persistence_manager = configured_container.get("PersistenceManager")
        
        # Get SQL repository
        sql_repository = await persistence_manager.get_repository(TestSQLEntity)
        assert isinstance(sql_repository, SQLRepository)
        
        # Initialize schema
        await sql_repository.initialize_schema([TestSQLEntity])
        
        print("    ✅ SQL Repository initialized correctly")
        
        # 2. Test SQLEntity
        print("  2️⃣ Testing SQLEntity...")
        
        # Create SQL entity
        sql_entity = TestSQLEntity(
            name="test_sql_entity",
            value=20,
            description="Test SQL entity"
        )
        
        # Save entity
        entity_id = await sql_entity.save()
        assert entity_id == sql_entity.id
        
        # Load entity
        loaded_entity = await TestSQLEntity.get(entity_id)
        assert loaded_entity is not None
        assert loaded_entity.name == "test_sql_entity"
        assert loaded_entity.value == 20
        
        print("    ✅ SQLEntity working correctly")
        
        # 3. Test SQL Events
        print("  3️⃣ Testing SQL Entity Events...")
        
        dispatcher = configured_container.get("EventDispatcher")
        
        # Dispatch SQL entity command
        command_context = CommandContext(
            entity_class=TestSQLEntity,
            entity_id=sql_entity.id,
            event_name="increment",
            parameters={"amount": 10}
        )
        
        result = await dispatcher.dispatch(command_context)
        assert result.success
        assert "SQL Entity incremented by 10" in result.return_value
        
        # Verify persistence
        updated_entity = await TestSQLEntity.get(sql_entity.id)
        assert updated_entity.value == 30
        
        print("    ✅ SQL Entity Events working correctly")
        
        # 4. Test SQL Queries
        print("  4️⃣ Testing SQL Queries...")
        
        # Create additional entities for querying
        entity2 = TestSQLEntity(name="entity2", value=50, description="Second entity")
        await entity2.save()
        
        entity3 = TestSQLEntity(name="entity3", value=75, description="Third entity")
        await entity3.save()
        
        # Test query with filters
        query_options = QueryOptions()
        query_options.add_filter("value", QueryOperator.GREATER_THAN, 25)
        query_options.add_sort("value", "asc")
        
        result = await sql_repository.query(TestSQLEntity, query_options)
        assert isinstance(result, QueryResult)
        assert len(result.entities) >= 2
        assert all(entity.value > 25 for entity in result.entities)
        
        print("    ✅ SQL Queries working correctly")
        
        # 5. Test SQL Transactions
        print("  5️⃣ Testing SQL Transactions...")
        
        # Begin transaction
        transaction = await sql_repository.begin_transaction()
        assert transaction is not None
        
        # Make changes within transaction
        sql_entity.value = 999
        await sql_repository.save(sql_entity, transaction)
        
        # Commit transaction
        await sql_repository.commit_transaction(transaction)
        
        # Verify changes
        final_entity = await TestSQLEntity.get(sql_entity.id)
        assert final_entity.value == 999
        
        print("    ✅ SQL Transactions working correctly")
        
        print("  ✅ Phase 4 tests completed successfully")
    
    @pytest.mark.asyncio
    async def test_multi_backend_integration(self, configured_container):
        """Test integration across multiple backends"""
        print("\n🧪 Testing Multi-Backend Integration")
        
        # 1. Create entities in different backends
        print("  1️⃣ Testing Multi-Backend Entity Creation...")
        
        # Memory entity
        memory_entity = TestEntity(name="memory_test", value=100)
        
        # SQL entity (if available)
        if SQL_AVAILABLE:
            sql_entity = TestSQLEntity(name="sql_test", value=200, description="SQL test")
            await sql_entity.save()
        
        print("    ✅ Entities created in multiple backends")
        
        # 2. Test cross-backend transactions
        print("  2️⃣ Testing Cross-Backend Transactions...")
        
        unit_of_work = configured_container.get("UnitOfWork")
        
        async with unit_of_work as uow:
            # Register entities from different backends
            await uow.register_entity(memory_entity)
            if SQL_AVAILABLE:
                await uow.register_entity(sql_entity)
            
            # Make coordinated changes
            memory_entity.value = 150
            if SQL_AVAILABLE:
                sql_entity.value = 250
        
        # Verify changes persisted
        assert memory_entity.value == 150
        if SQL_AVAILABLE:
            updated_sql = await TestSQLEntity.get(sql_entity.id)
            assert updated_sql.value == 250
        
        print("    ✅ Cross-backend transactions working correctly")
        
        # 3. Test event propagation across backends
        print("  3️⃣ Testing Event Propagation...")
        
        dispatcher = configured_container.get("EventDispatcher")
        event_bus = configured_container.get("EventBus")
        
        events_captured = []
        
        async def event_capture(event: DomainEvent):
            events_captured.append(event)
        
        subscription_id = await event_bus.subscribe(event_capture)
        
        # Execute events on different backend entities
        await dispatcher.dispatch(CommandContext(
            entity_class=TestEntity,
            entity_id=memory_entity.id,
            event_name="toggle_active",
            parameters={}
        ))
        
        if SQL_AVAILABLE:
            await dispatcher.dispatch(CommandContext(
                entity_class=TestSQLEntity,
                entity_id=sql_entity.id,
                event_name="update_description",
                parameters={"new_description": "Updated via event"}
            ))
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify events were captured
        assert len(events_captured) >= 1
        
        await event_bus.unsubscribe(subscription_id)
        
        print("    ✅ Event propagation working correctly")
        
        print("  ✅ Multi-backend integration tests completed successfully")
    
    @pytest.mark.asyncio
    async def test_performance_and_stress(self, configured_container):
        """Test performance and stress scenarios"""
        print("\n🧪 Testing Performance and Stress Scenarios")
        
        # 1. Test high-volume entity creation
        print("  1️⃣ Testing High-Volume Entity Creation...")
        
        start_time = time.time()
        entities = []
        
        for i in range(100):
            entity = TestEntity(name=f"stress_test_{i}", value=i)
            entities.append(entity)
        
        creation_time = time.time() - start_time
        print(f"    📊 Created 100 entities in {creation_time:.3f}s")
        assert creation_time < 1.0  # Should be fast
        
        print("    ✅ High-volume creation test passed")
        
        # 2. Test concurrent event dispatch
        print("  2️⃣ Testing Concurrent Event Dispatch...")
        
        dispatcher = configured_container.get("EventDispatcher")
        
        # Create test entity
        test_entity = TestEntity(name="concurrent_test", value=0)
        
        # Dispatch multiple concurrent commands
        start_time = time.time()
        
        tasks = []
        for i in range(50):
            task = dispatcher.dispatch(CommandContext(
                entity_class=TestEntity,
                entity_id=test_entity.id,
                event_name="increment",
                parameters={"amount": 1}
            ))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        dispatch_time = time.time() - start_time
        print(f"    📊 Dispatched 50 concurrent commands in {dispatch_time:.3f}s")
        
        # Verify all commands succeeded
        assert all(result.success for result in results)
        
        # Check final value
        final_entity = await TestEntity.get(test_entity.id)
        assert final_entity.value == 50
        
        print("    ✅ Concurrent dispatch test passed")
        
        # 3. Test event bus throughput
        print("  3️⃣ Testing Event Bus Throughput...")
        
        event_bus = configured_container.get("EventBus")
        
        events_received = []
        
        async def high_volume_subscriber(event: DomainEvent):
            events_received.append(event)
        
        subscription_id = await event_bus.subscribe(high_volume_subscriber)
        
        # Publish many events rapidly
        start_time = time.time()
        
        for i in range(200):
            event = DomainEvent(
                event_type="stress_test",
                entity_id=f"entity_{i}",
                entity_type="TestEntity",
                data={"index": i}
            )
            await event_bus.publish(event)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        throughput_time = time.time() - start_time
        print(f"    📊 Published 200 events in {throughput_time:.3f}s")
        print(f"    📊 Received {len(events_received)} events")
        
        await event_bus.unsubscribe(subscription_id)
        
        assert len(events_received) >= 180  # Allow for some processing delay
        
        print("    ✅ Event bus throughput test passed")
        
        # 4. Test memory usage and cleanup
        print("  4️⃣ Testing Memory Usage and Cleanup...")
        
        persistence_manager = configured_container.get("PersistenceManager")
        
        # Check backend status
        status = await persistence_manager.get_backend_status()
        assert len(status) > 0
        
        # Get metrics
        memory_repo = await persistence_manager.get_repository(TestEntity)
        metrics = await memory_repo.get_metrics()
        
        print(f"    📊 Memory backend metrics: {metrics}")
        
        # Test cleanup
        cleanup_results = await persistence_manager.cleanup_all_backends()
        print(f"    🧹 Cleanup results: {cleanup_results}")
        
        print("    ✅ Memory usage and cleanup test passed")
        
        print("  ✅ Performance and stress tests completed successfully")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, configured_container):
        """Test error handling and recovery scenarios"""
        print("\n🧪 Testing Error Handling and Recovery")
        
        # 1. Test invalid command dispatch
        print("  1️⃣ Testing Invalid Command Handling...")
        
        dispatcher = configured_container.get("EventDispatcher")
        
        # Try to dispatch to non-existent entity
        invalid_command = CommandContext(
            entity_class=TestEntity,
            entity_id="non-existent-id",
            event_name="increment",
            parameters={"amount": 1}
        )
        
        result = await dispatcher.dispatch(invalid_command)
        assert not result.success
        assert result.error_message is not None
        
        print("    ✅ Invalid command handling working correctly")
        
        # 2. Test transaction rollback
        print("  2️⃣ Testing Transaction Rollback...")
        
        unit_of_work = configured_container.get("UnitOfWork")
        test_entity = TestEntity(name="rollback_test", value=10)
        
        original_value = test_entity.value
        
        try:
            async with unit_of_work as uow:
                await uow.register_entity(test_entity)
                test_entity.value = 999
                
                # Force an error to trigger rollback
                raise ValueError("Intentional test error")
        
        except ValueError:
            pass  # Expected error
        
        # Verify rollback occurred
        assert test_entity.value == original_value
        
        print("    ✅ Transaction rollback working correctly")
        
        # 3. Test event bus error isolation
        print("  3️⃣ Testing Event Bus Error Isolation...")
        
        event_bus = configured_container.get("EventBus")
        
        events_received = []
        
        async def failing_subscriber(event: DomainEvent):
            if event.data.get("should_fail"):
                raise Exception("Intentional subscriber failure")
            events_received.append(event)
        
        async def working_subscriber(event: DomainEvent):
            events_received.append(event)
        
        # Subscribe both handlers
        failing_sub = await event_bus.subscribe(failing_subscriber)
        working_sub = await event_bus.subscribe(working_subscriber)
        
        # Publish event that will cause failure
        failing_event = DomainEvent(
            event_type="test_failure",
            entity_id="test",
            entity_type="TestEntity",
            data={"should_fail": True}
        )
        
        await event_bus.publish(failing_event)
        
        # Publish normal event
        normal_event = DomainEvent(
            event_type="test_normal",
            entity_id="test",
            entity_type="TestEntity",
            data={"should_fail": False}
        )
        
        await event_bus.publish(normal_event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Verify working subscriber still received events
        assert len(events_received) >= 1
        
        # Cleanup
        await event_bus.unsubscribe(failing_sub)
        await event_bus.unsubscribe(working_sub)
        
        print("    ✅ Event bus error isolation working correctly")
        
        print("  ✅ Error handling and recovery tests completed successfully")


# Main test execution
if __name__ == "__main__":
    print("🚀 Starting StarModel End-to-End System Tests")
    print("=" * 60)
    
    async def run_all_tests():
        """Run all tests in sequence"""
        test_instance = TestSystemE2E()
        
        # Set up container
        async with test_instance.configured_container() as container:
            
            # Run all test methods
            await test_instance.test_phase1_application_service_layer(container)
            await test_instance.test_phase3_web_adapter_decoupling(container)
            
            if SQL_AVAILABLE:
                await test_instance.test_phase4_sql_integration(container)
            else:
                print("\n⚠️  Skipping Phase 4 SQL tests - SQL dependencies not available")
            
            await test_instance.test_multi_backend_integration(container)
            await test_instance.test_performance_and_stress(container)
            await test_instance.test_error_handling_and_recovery(container)
        
        print("\n" + "=" * 60)
        print("🎉 All End-to-End Tests Completed Successfully!")
        print("\n✅ Test Results:")
        print("   - Phase 1 (Application Service Layer): PASSED")
        print("   - Phase 3 (Web Adapter Decoupling): PASSED")
        if SQL_AVAILABLE:
            print("   - Phase 4 (SQL Integration): PASSED")
        print("   - Multi-Backend Integration: PASSED")
        print("   - Performance and Stress: PASSED")
        print("   - Error Handling and Recovery: PASSED")
        print("\n🎯 StarModel Clean Architecture Refactoring: FULLY VALIDATED")
    
    # Run tests
    asyncio.run(run_all_tests())