"""
FastState SSE Connection Management

This module implements advanced SSE connection management with scope-aware broadcasting
and connection pooling for real-time state synchronization.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from uuid import uuid4

from datastar_py import ServerSentEventGenerator as SSE
from fasthtml.common import Request

from .registry import StateScope


@dataclass
class SSEConnection:
    """Represents an active SSE connection with state subscriptions."""
    
    connection_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    subscribed_states: Set[str] = field(default_factory=set)
    subscribed_records: Set[str] = field(default_factory=set)
    is_active: bool = True
    
    # Weak reference to the actual SSE generator/response
    _sse_generator: Optional[Any] = None
    
    def __post_init__(self):
        """Initialize connection after creation."""
        self.last_heartbeat = time.time()
    
    def is_expired(self, timeout: int = 300) -> bool:
        """Check if connection has expired based on last heartbeat."""
        return time.time() - self.last_heartbeat > timeout
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp."""
        self.last_heartbeat = time.time()
    
    def subscribe_to_state(self, state_class_name: str):
        """Subscribe this connection to state changes for a specific state class."""
        self.subscribed_states.add(state_class_name)
    
    def subscribe_to_record(self, record_key: str):
        """Subscribe this connection to changes for a specific record."""
        self.subscribed_records.add(record_key)
    
    def unsubscribe_from_state(self, state_class_name: str):
        """Unsubscribe from state changes for a specific state class."""
        self.subscribed_states.discard(state_class_name)
    
    def unsubscribe_from_record(self, record_key: str):
        """Unsubscribe from record changes."""
        self.subscribed_records.discard(record_key)


class StateSSEManager:
    """
    Manages SSE connections and handles scope-aware broadcasting of state changes.
    
    This class provides connection pooling, automatic cleanup, and efficient
    broadcasting based on state scopes (GLOBAL, SESSION, USER, RECORD).
    """
    
    def __init__(self, connection_timeout: int = 300, cleanup_interval: int = 60):
        """
        Initialize the SSE manager.
        
        Args:
            connection_timeout: Seconds before inactive connections are considered expired
            cleanup_interval: Seconds between cleanup cycles for expired connections
        """
        self.connection_timeout = connection_timeout
        self.cleanup_interval = cleanup_interval
        
        # Connection storage
        self.connections: Dict[str, SSEConnection] = {}
        
        # Lookup indexes for efficient broadcasting
        self.connections_by_session: Dict[str, Set[str]] = defaultdict(set)
        self.connections_by_user: Dict[str, Set[str]] = defaultdict(set)
        self.connections_by_state: Dict[str, Set[str]] = defaultdict(set)
        self.connections_by_record: Dict[str, Set[str]] = defaultdict(set)
        
        # Event queues for async broadcasting
        self.broadcast_queues: Dict[str, asyncio.Queue] = {}
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background task for cleaning up expired connections."""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                loop = asyncio.get_event_loop()
                self._cleanup_task = loop.create_task(self._cleanup_expired_connections())
            except RuntimeError:
                # No event loop running, cleanup will happen manually
                pass
    
    async def _cleanup_expired_connections(self):
        """Background task to clean up expired connections."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self.cleanup_expired_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue cleanup
                print(f"Error in connection cleanup: {e}")
    
    def create_connection(
        self, 
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        subscribed_states: Optional[List[str]] = None
    ) -> SSEConnection:
        """
        Create a new SSE connection with state subscriptions.
        
        Args:
            session_id: Session identifier for session-scoped broadcasting
            user_id: User identifier for user-scoped broadcasting
            subscribed_states: List of state class names to subscribe to
            
        Returns:
            New SSEConnection instance
        """
        connection = SSEConnection(
            session_id=session_id,
            user_id=user_id,
            subscribed_states=set(subscribed_states or [])
        )
        
        # Store connection
        self.connections[connection.connection_id] = connection
        
        # Update indexes
        if session_id:
            self.connections_by_session[session_id].add(connection.connection_id)
        
        if user_id:
            self.connections_by_user[user_id].add(connection.connection_id)
        
        for state_name in connection.subscribed_states:
            self.connections_by_state[state_name].add(connection.connection_id)
        
        # Create broadcast queue for this connection
        self.broadcast_queues[connection.connection_id] = asyncio.Queue()
        
        return connection
    
    def remove_connection(self, connection_id: str):
        """Remove a connection and clean up all indexes."""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        # Remove from indexes
        if connection.session_id:
            self.connections_by_session[connection.session_id].discard(connection_id)
            if not self.connections_by_session[connection.session_id]:
                del self.connections_by_session[connection.session_id]
        
        if connection.user_id:
            self.connections_by_user[connection.user_id].discard(connection_id)
            if not self.connections_by_user[connection.user_id]:
                del self.connections_by_user[connection.user_id]
        
        for state_name in connection.subscribed_states:
            self.connections_by_state[state_name].discard(connection_id)
            if not self.connections_by_state[state_name]:
                del self.connections_by_state[state_name]
        
        for record_key in connection.subscribed_records:
            self.connections_by_record[record_key].discard(connection_id)
            if not self.connections_by_record[record_key]:
                del self.connections_by_record[record_key]
        
        # Clean up connection and queue
        del self.connections[connection_id]
        if connection_id in self.broadcast_queues:
            del self.broadcast_queues[connection_id]
    
    def cleanup_expired_connections(self):
        """Clean up expired connections based on heartbeat timeout."""
        expired_connections = [
            conn_id for conn_id, conn in self.connections.items()
            if conn.is_expired(self.connection_timeout)
        ]
        
        for conn_id in expired_connections:
            self.remove_connection(conn_id)
    
    def update_heartbeat(self, connection_id: str):
        """Update heartbeat for a specific connection."""
        connection = self.connections.get(connection_id)
        if connection:
            connection.update_heartbeat()
    
    def broadcast_state_change(
        self,
        state_class_name: str,
        state_changes: Dict[str, Any],
        scope: StateScope,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        record_id: Optional[str] = None
    ):
        """
        Broadcast state changes to appropriate connections based on scope.
        
        Args:
            state_class_name: Name of the state class that changed
            state_changes: Dictionary of changed state properties
            scope: State scope determining broadcast targets
            session_id: Session ID for session-scoped broadcasts
            user_id: User ID for user-scoped broadcasts
            record_id: Record ID for record-scoped broadcasts
        """
        target_connections = self._get_target_connections(
            scope, state_class_name, session_id, user_id, record_id
        )
        
        if not target_connections:
            return
        
        # Create SSE event
        sse_event = SSE.merge_signals(state_changes)
        
        # Queue event for each target connection
        for conn_id in target_connections:
            if conn_id in self.broadcast_queues:
                try:
                    self.broadcast_queues[conn_id].put_nowait(sse_event)
                except asyncio.QueueFull:
                    # Connection queue is full, consider removing connection
                    self.remove_connection(conn_id)
    
    def _get_target_connections(
        self,
        scope: StateScope,
        state_class_name: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        record_id: Optional[str] = None
    ) -> Set[str]:
        """
        Get target connection IDs based on scope and context.
        
        Returns:
            Set of connection IDs that should receive the broadcast
        """
        target_connections = set()
        
        if scope == StateScope.GLOBAL:
            # Broadcast to all connections subscribed to this state
            target_connections = self.connections_by_state.get(state_class_name, set()).copy()
        
        elif scope == StateScope.SESSION and session_id:
            # Broadcast to connections in the same session
            session_connections = self.connections_by_session.get(session_id, set())
            state_connections = self.connections_by_state.get(state_class_name, set())
            target_connections = session_connections.intersection(state_connections)
        
        elif scope == StateScope.USER and user_id:
            # Broadcast to all connections for the same user
            user_connections = self.connections_by_user.get(user_id, set())
            state_connections = self.connections_by_state.get(state_class_name, set())
            target_connections = user_connections.intersection(state_connections)
        
        elif scope == StateScope.RECORD and record_id:
            # Broadcast to connections subscribed to the specific record
            record_key = f"{state_class_name}:{record_id}"
            target_connections = self.connections_by_record.get(record_key, set()).copy()
        
        elif scope == StateScope.COMPONENT:
            # Component scope is more specific, only direct subscribers
            target_connections = self.connections_by_state.get(state_class_name, set()).copy()
        
        return target_connections
    
    def subscribe_connection_to_record(self, connection_id: str, state_class_name: str, record_id: str):
        """Subscribe a connection to a specific record."""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        record_key = f"{state_class_name}:{record_id}"
        connection.subscribe_to_record(record_key)
        self.connections_by_record[record_key].add(connection_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections."""
        active_connections = sum(1 for conn in self.connections.values() if conn.is_active)
        
        return {
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "connections_by_session": len(self.connections_by_session),
            "connections_by_user": len(self.connections_by_user),
            "subscribed_states": len(self.connections_by_state),
            "subscribed_records": len(self.connections_by_record),
        }
    
    async def get_sse_stream(self, connection_id: str):
        """
        Get an async generator for SSE events for a specific connection.
        
        This method provides the actual SSE stream that can be returned
        as a FastHTML StreamingResponse.
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        queue = self.broadcast_queues.get(connection_id)
        if not queue:
            return
        
        try:
            # Send initial heartbeat - use a simple SSE format
            yield f"data: {{'type': 'heartbeat', 'timestamp': {time.time()}}}\n\n"
            
            while connection.is_active and not connection.is_expired(self.connection_timeout):
                try:
                    # Wait for next event with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                    connection.update_heartbeat()
                    
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"data: {{'type': 'heartbeat', 'timestamp': {time.time()}}}\n\n"
                    connection.update_heartbeat()
                
                except Exception as e:
                    # Log error and break
                    print(f"Error in SSE stream for connection {connection_id}: {e}")
                    break
        
        finally:
            # Clean up connection
            self.remove_connection(connection_id)
    
    def __del__(self):
        """Clean up background tasks when manager is destroyed."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


# Global SSE manager instance
sse_manager = StateSSEManager()