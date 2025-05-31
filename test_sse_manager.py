#!/usr/bin/env python3
"""
Test SSE Manager Functionality (Phase 4.1)

This test verifies that the SSE connection management system works correctly
with scope-aware broadcasting and connection pooling.
"""

import sys
import os
import asyncio
import time
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from faststate.sse_manager import StateSSEManager, SSEConnection
from faststate.registry import StateScope


def test_sse_connection_creation():
    """Test SSE connection creation and management."""
    print("Testing SSE Connection Creation...")
    
    manager = StateSSEManager()
    
    # Test connection creation
    connection = manager.create_connection(
        session_id="test_session",
        user_id="test_user",
        subscribed_states=["MyState", "AnotherState"]
    )
    
    assert connection.session_id == "test_session"
    assert connection.user_id == "test_user"
    assert "MyState" in connection.subscribed_states
    assert "AnotherState" in connection.subscribed_states
    assert connection.connection_id in manager.connections
    
    print("✓ Connection creation works")
    
    # Test connection indexing
    assert connection.connection_id in manager.connections_by_session["test_session"]
    assert connection.connection_id in manager.connections_by_user["test_user"]
    assert connection.connection_id in manager.connections_by_state["MyState"]
    assert connection.connection_id in manager.connections_by_state["AnotherState"]
    
    print("✓ Connection indexing works")
    
    # Test connection removal
    manager.remove_connection(connection.connection_id)
    assert connection.connection_id not in manager.connections
    assert len(manager.connections_by_session.get("test_session", set())) == 0
    assert len(manager.connections_by_user.get("test_user", set())) == 0
    
    print("✓ Connection removal works")


def test_scope_aware_broadcasting():
    """Test scope-aware broadcasting functionality."""
    print("Testing Scope-Aware Broadcasting...")
    
    manager = StateSSEManager()
    
    # Create connections for different scopes
    global_conn = manager.create_connection(
        session_id="session1",
        subscribed_states=["GlobalState"]
    )
    
    session_conn1 = manager.create_connection(
        session_id="session1",
        subscribed_states=["SessionState"]
    )
    
    session_conn2 = manager.create_connection(
        session_id="session2",
        subscribed_states=["SessionState"]
    )
    
    user_conn1 = manager.create_connection(
        session_id="session1",
        user_id="user1",
        subscribed_states=["UserState"]
    )
    
    user_conn2 = manager.create_connection(
        session_id="session3",
        user_id="user1",
        subscribed_states=["UserState"]
    )
    
    # Test global broadcasting
    target_connections = manager._get_target_connections(
        StateScope.GLOBAL, "GlobalState"
    )
    assert global_conn.connection_id in target_connections
    print("✓ Global scope broadcasting works")
    
    # Test session broadcasting
    target_connections = manager._get_target_connections(
        StateScope.SESSION, "SessionState", session_id="session1"
    )
    assert session_conn1.connection_id in target_connections
    assert session_conn2.connection_id not in target_connections
    print("✓ Session scope broadcasting works")
    
    # Test user broadcasting
    target_connections = manager._get_target_connections(
        StateScope.USER, "UserState", user_id="user1"
    )
    assert user_conn1.connection_id in target_connections
    assert user_conn2.connection_id in target_connections
    print("✓ User scope broadcasting works")
    
    # Clean up
    for conn_id in list(manager.connections.keys()):
        manager.remove_connection(conn_id)


def test_connection_heartbeat_and_expiry():
    """Test connection heartbeat and expiry functionality."""
    print("Testing Connection Heartbeat and Expiry...")
    
    manager = StateSSEManager(connection_timeout=1)  # 1 second timeout for testing
    
    # Create connection
    connection = manager.create_connection(session_id="test_session")
    conn_id = connection.connection_id
    
    # Test heartbeat
    original_heartbeat = connection.last_heartbeat
    time.sleep(0.1)
    manager.update_heartbeat(conn_id)
    assert connection.last_heartbeat > original_heartbeat
    print("✓ Heartbeat update works")
    
    # Test expiry detection
    connection.last_heartbeat = time.time() - 2  # Make it expired
    assert connection.is_expired(1)
    print("✓ Expiry detection works")
    
    # Test cleanup
    manager.cleanup_expired_connections()
    assert conn_id not in manager.connections
    print("✓ Expired connection cleanup works")


def test_record_subscription():
    """Test record-specific subscription functionality."""
    print("Testing Record Subscription...")
    
    manager = StateSSEManager()
    
    # Create connection
    connection = manager.create_connection(
        session_id="test_session",
        subscribed_states=["RecordState"]
    )
    
    # Subscribe to specific record
    manager.subscribe_connection_to_record(
        connection.connection_id, "RecordState", "record123"
    )
    
    # Check subscription
    record_key = "RecordState:record123"
    assert record_key in connection.subscribed_records
    assert connection.connection_id in manager.connections_by_record[record_key]
    
    print("✓ Record subscription works")
    
    # Test record broadcasting
    target_connections = manager._get_target_connections(
        StateScope.RECORD, "RecordState", record_id="record123"
    )
    assert connection.connection_id in target_connections
    
    print("✓ Record scope broadcasting works")


def test_state_change_broadcasting():
    """Test state change broadcasting."""
    print("Testing State Change Broadcasting...")
    
    manager = StateSSEManager()
    
    # Create connections
    conn1 = manager.create_connection(
        session_id="session1",
        subscribed_states=["TestState"]
    )
    
    conn2 = manager.create_connection(
        session_id="session2", 
        subscribed_states=["TestState"]
    )
    
    # Test broadcasting
    state_changes = {"count": 42, "name": "updated"}
    
    # This should queue events for both connections
    manager.broadcast_state_change(
        state_class_name="TestState",
        state_changes=state_changes,
        scope=StateScope.GLOBAL
    )
    
    # Check that events were queued
    assert not manager.broadcast_queues[conn1.connection_id].empty()
    assert not manager.broadcast_queues[conn2.connection_id].empty()
    
    print("✓ State change broadcasting works")


def test_connection_stats():
    """Test connection statistics."""
    print("Testing Connection Statistics...")
    
    manager = StateSSEManager()
    
    # Create some connections
    for i in range(3):
        manager.create_connection(
            session_id=f"session{i}",
            user_id=f"user{i}",
            subscribed_states=["TestState"]
        )
    
    stats = manager.get_connection_stats()
    assert stats["total_connections"] == 3
    assert stats["active_connections"] == 3
    assert stats["connections_by_session"] == 3
    assert stats["connections_by_user"] == 3
    assert stats["subscribed_states"] == 1
    
    print("✓ Connection statistics work")


async def test_sse_stream():
    """Test SSE stream generation."""
    print("Testing SSE Stream Generation...")
    
    manager = StateSSEManager()
    
    # Create connection
    connection = manager.create_connection(
        session_id="test_session",
        subscribed_states=["TestState"]
    )
    
    # Queue some test events
    queue = manager.broadcast_queues[connection.connection_id]
    await queue.put("data: test event 1\n\n")
    
    # Get stream and collect first few events
    events = []
    stream_gen = manager.get_sse_stream(connection.connection_id)
    
    try:
        # Get heartbeat
        heartbeat = await stream_gen.__anext__()
        events.append(heartbeat)
        
        # Get test event
        test_event = await stream_gen.__anext__()
        events.append(test_event)
        
        # Mark connection as inactive to clean up
        connection.is_active = False
        
    except StopAsyncIteration:
        pass
    
    assert len(events) >= 2  # heartbeat + test event
    assert "heartbeat" in events[0]
    assert "test event 1" in events[1]
    
    print("✓ SSE stream generation works")


def run_all_tests():
    """Run all SSE manager tests."""
    print("Testing FastState SSE Manager System...")
    print("=" * 50)
    
    test_sse_connection_creation()
    test_scope_aware_broadcasting()
    test_connection_heartbeat_and_expiry()
    test_record_subscription()
    test_state_change_broadcasting()
    test_connection_stats()
    
    # Run async test
    asyncio.run(test_sse_stream())
    
    print("=" * 50)
    print("✅ All SSE Manager tests passed!")


if __name__ == "__main__":
    run_all_tests()