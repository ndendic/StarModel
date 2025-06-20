"""
SSE Broadcaster - Server-Sent Events Broadcasting System

⚡ Real-time Event Broadcasting:
This module provides Server-Sent Events broadcasting capabilities for
distributing domain events to connected clients in real-time, enabling
live updates and reactive UI synchronization.

Key Features:
- Event bus integration for domain event broadcasting
- Client connection management with automatic cleanup
- Filtered event streams per client
- Connection heartbeat and reconnection handling
- Scalable multi-client broadcasting
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import weakref
from concurrent.futures import ThreadPoolExecutor

from ...events.streaming.event_bus import EventBus, DomainEvent, EventFilter
from ...infrastructure.web.interfaces import WebRequest, WebResponse
from .protocols.response_formatters import DatastarSSEFormatter, FormatterContext

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """Connection state enumeration"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"

@dataclass
class ClientConnection:
    """Represents an active client connection"""
    id: str
    request: WebRequest
    state: ConnectionState = ConnectionState.CONNECTING
    created_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    subscriptions: Set[str] = field(default_factory=set)
    event_filters: List[EventFilter] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Internal connection management
    _event_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000))
    _heartbeat_task: Optional[asyncio.Task] = None
    _cleanup_callbacks: List[Callable] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize connection after creation"""
        # Extract user and session info from request
        if self.request:
            self.user_id = self.request.get_user()
            session_data = self.request.get_session()
            self.session_id = session_data.get('session_id')
            
            # Set up default subscriptions based on user
            if self.user_id:
                self.subscriptions.add(f"user:{self.user_id}")
            if self.session_id:
                self.subscriptions.add(f"session:{self.session_id}")
    
    def add_event_filter(self, event_filter: EventFilter):
        """Add event filter for this connection"""
        self.event_filters.append(event_filter)
    
    def matches_event(self, event: DomainEvent) -> bool:
        """Check if event matches this connection's filters"""
        # Check subscriptions first
        for subscription in self.subscriptions:
            if subscription in event.metadata.get('channels', []):
                return True
        
        # Check event filters
        for event_filter in self.event_filters:
            if event_filter.matches(event):
                return True
        
        return False
    
    async def send_event(self, event: DomainEvent):
        """Send event to this connection"""
        try:
            await self._event_queue.put(event)
        except asyncio.QueueFull:
            logger.warning(f"Event queue full for connection {self.id}, dropping event")
    
    async def get_next_event(self, timeout: float = 30.0) -> Optional[DomainEvent]:
        """Get next event for this connection"""
        try:
            return await asyncio.wait_for(
                self._event_queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        self.last_heartbeat = datetime.now()
    
    def is_alive(self, timeout: timedelta = timedelta(minutes=5)) -> bool:
        """Check if connection is still alive"""
        return (
            self.state == ConnectionState.CONNECTED and
            datetime.now() - self.last_heartbeat < timeout
        )
    
    def add_cleanup_callback(self, callback: Callable):
        """Add cleanup callback for connection termination"""
        self._cleanup_callbacks.append(callback)
    
    async def cleanup(self):
        """Cleanup connection resources"""
        self.state = ConnectionState.DISCONNECTING
        
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Run cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in cleanup callback: {e}")
        
        self.state = ConnectionState.DISCONNECTED

class SSEBroadcaster:
    """
    Server-Sent Events broadcaster for real-time event distribution.
    
    Manages client connections and broadcasts domain events to subscribed
    clients using Server-Sent Events protocol.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        formatter: Optional[DatastarSSEFormatter] = None,
        heartbeat_interval: float = 30.0,
        connection_timeout: float = 300.0,
        max_connections: int = 10000
    ):
        self.event_bus = event_bus
        self.formatter = formatter or DatastarSSEFormatter(include_debug_info=True)
        self.heartbeat_interval = heartbeat_interval
        self.connection_timeout = connection_timeout
        self.max_connections = max_connections
        
        # Connection management
        self._connections: Dict[str, ClientConnection] = {}
        self._connection_lock = asyncio.Lock()
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._metrics = {
            'connections_created': 0,
            'connections_closed': 0,
            'events_broadcast': 0,
            'events_filtered': 0,
            'heartbeats_sent': 0,
            'errors': 0
        }
        
        # Event subscription
        self._event_subscription_id = None
    
    async def start(self):
        """Start the SSE broadcaster"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting SSE broadcaster...")
        
        # Subscribe to event bus
        self._event_subscription_id = await self.event_bus.subscribe(
            self._handle_domain_event,
            event_filter=EventFilter()  # Subscribe to all events
        )
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_connections())
        self._broadcast_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info("SSE broadcaster started successfully")
    
    async def stop(self):
        """Stop the SSE broadcaster"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping SSE broadcaster...")
        
        # Unsubscribe from event bus
        if self._event_subscription_id:
            await self.event_bus.unsubscribe(self._event_subscription_id)
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._connection_lock:
            for connection in list(self._connections.values()):
                await connection.cleanup()
            self._connections.clear()
        
        logger.info("SSE broadcaster stopped")
    
    async def create_connection(self, request: WebRequest) -> ClientConnection:
        """Create a new SSE connection"""
        async with self._connection_lock:
            if len(self._connections) >= self.max_connections:
                raise ConnectionError("Maximum connections exceeded")
            
            # Generate connection ID
            connection_id = f"sse_{datetime.now().timestamp()}_{len(self._connections)}"
            
            # Create connection
            connection = ClientConnection(
                id=connection_id,
                request=request,
                state=ConnectionState.CONNECTING
            )
            
            # Store connection
            self._connections[connection_id] = connection
            self._metrics['connections_created'] += 1
            
            # Set up cleanup callback
            connection.add_cleanup_callback(
                lambda: self._remove_connection(connection_id)
            )
            
            logger.info(f"Created SSE connection: {connection_id}")
            return connection
    
    async def _remove_connection(self, connection_id: str):
        """Remove connection from active connections"""
        async with self._connection_lock:
            if connection_id in self._connections:
                del self._connections[connection_id]
                self._metrics['connections_closed'] += 1
                logger.info(f"Removed SSE connection: {connection_id}")
    
    async def get_connection_stream(self, connection: ClientConnection) -> AsyncIterator[str]:
        """Get SSE stream for a connection"""
        connection.state = ConnectionState.CONNECTED
        
        try:
            # Send initial connection event
            yield f"event: connection\n"
            yield f"data: {json.dumps({'type': 'connected', 'connection_id': connection.id})}\n\n"
            
            while self._running and connection.state == ConnectionState.CONNECTED:
                # Get next event (with timeout for heartbeat)
                event = await connection.get_next_event(timeout=self.heartbeat_interval)
                
                if event:
                    # Format event using formatter
                    try:
                        # Create formatter context
                        formatter_context = FormatterContext(
                            request=connection.request,
                            user_id=connection.user_id,
                            session_id=connection.session_id,
                            client_capabilities=connection.metadata.get('capabilities', {}),
                            format_preferences=connection.metadata.get('preferences', {})
                        )
                        
                        # Convert domain event to command result for formatting
                        from ...events.dispatching.command_context import CommandResult
                        command_result = CommandResult(
                            command_id=event.event_id,
                            success=True,
                            return_value=event.data,
                            signals_updated=event.data if isinstance(event.data, dict) else {},
                            fragments_generated=[],
                            events_published=[event.event_type],
                            execution_time_ms=0.0
                        )
                        
                        # Format as SSE
                        formatted_response = await self.formatter.format_response(
                            command_result,
                            formatter_context
                        )
                        
                        # Extract SSE data from formatted response
                        if hasattr(formatted_response, '_streaming_generator'):
                            async for sse_chunk in formatted_response._streaming_generator:
                                yield sse_chunk
                        
                        connection.update_heartbeat()
                        
                    except Exception as e:
                        logger.error(f"Error formatting event for connection {connection.id}: {e}")
                        self._metrics['errors'] += 1
                        
                        # Send error event
                        yield f"event: error\n"
                        yield f"data: {json.dumps({'type': 'format_error', 'message': str(e)})}\n\n"
                
                else:
                    # Send heartbeat
                    yield f"event: heartbeat\n"
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                    connection.update_heartbeat()
                    self._metrics['heartbeats_sent'] += 1
        
        except Exception as e:
            logger.error(f"Error in SSE stream for connection {connection.id}: {e}")
            self._metrics['errors'] += 1
        
        finally:
            # Cleanup connection
            await connection.cleanup()
    
    async def _handle_domain_event(self, event: DomainEvent):
        """Handle domain event from event bus"""
        if not self._running:
            return
        
        matching_connections = []
        
        # Find matching connections
        async with self._connection_lock:
            for connection in self._connections.values():
                if connection.state == ConnectionState.CONNECTED:
                    if connection.matches_event(event):
                        matching_connections.append(connection)
                    else:
                        self._metrics['events_filtered'] += 1
        
        # Send event to matching connections
        if matching_connections:
            self._metrics['events_broadcast'] += 1
            
            # Send to all matching connections concurrently
            await asyncio.gather(
                *[connection.send_event(event) for connection in matching_connections],
                return_exceptions=True
            )
            
            logger.debug(f"Broadcast event {event.event_type} to {len(matching_connections)} connections")
    
    async def _cleanup_connections(self):
        """Background task to cleanup dead connections"""
        while self._running:
            try:
                current_time = datetime.now()
                cleanup_threshold = timedelta(seconds=self.connection_timeout)
                
                connections_to_cleanup = []
                
                async with self._connection_lock:
                    for connection in list(self._connections.values()):
                        if not connection.is_alive() or (current_time - connection.last_heartbeat) > cleanup_threshold:
                            connections_to_cleanup.append(connection)
                
                # Cleanup dead connections
                for connection in connections_to_cleanup:
                    logger.info(f"Cleaning up dead connection: {connection.id}")
                    await connection.cleanup()
                
                # Sleep before next cleanup
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")
                await asyncio.sleep(10)  # Shorter sleep on error
    
    async def _heartbeat_loop(self):
        """Background task for sending heartbeats"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Heartbeats are sent in get_connection_stream when no events are available
                # This loop just ensures we're checking regularly
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)
    
    async def subscribe_connection(
        self,
        connection_id: str,
        channels: List[str],
        event_filters: Optional[List[EventFilter]] = None
    ):
        """Subscribe connection to specific channels and event filters"""
        async with self._connection_lock:
            connection = self._connections.get(connection_id)
            if not connection:
                raise ValueError(f"Connection {connection_id} not found")
            
            # Add channel subscriptions
            connection.subscriptions.update(channels)
            
            # Add event filters
            if event_filters:
                connection.event_filters.extend(event_filters)
            
            logger.info(f"Updated subscriptions for connection {connection_id}: {channels}")
    
    async def unsubscribe_connection(
        self,
        connection_id: str,
        channels: List[str]
    ):
        """Unsubscribe connection from specific channels"""
        async with self._connection_lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return
            
            # Remove channel subscriptions
            connection.subscriptions.difference_update(channels)
            
            logger.info(f"Removed subscriptions for connection {connection_id}: {channels}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get broadcaster metrics"""
        return {
            **self._metrics,
            'active_connections': len(self._connections),
            'running': self._running,
            'heartbeat_interval': self.heartbeat_interval,
            'connection_timeout': self.connection_timeout
        }
    
    def get_connection_info(self) -> List[Dict[str, Any]]:
        """Get information about active connections"""
        return [
            {
                'id': conn.id,
                'state': conn.state.value,
                'created_at': conn.created_at.isoformat(),
                'last_heartbeat': conn.last_heartbeat.isoformat(),
                'user_id': conn.user_id,
                'session_id': conn.session_id,
                'subscriptions': list(conn.subscriptions),
                'event_filters': len(conn.event_filters)
            }
            for conn in self._connections.values()
        ]

class SSEBroadcastHandler:
    """
    HTTP handler for SSE broadcast endpoint.
    
    Handles incoming SSE connection requests and provides
    the streaming response with real-time event updates.
    """
    
    def __init__(self, broadcaster: SSEBroadcaster):
        self.broadcaster = broadcaster
    
    async def handle_connection(self, request: WebRequest) -> WebResponse:
        """Handle new SSE connection request"""
        try:
            # Create connection
            connection = await self.broadcaster.create_connection(request)
            
            # Create streaming response
            from ...infrastructure.web.interfaces import WebResponse
            
            class SSEStreamingResponse(WebResponse):
                """Streaming SSE response"""
                
                def __init__(self, broadcaster, connection):
                    super().__init__()
                    self.broadcaster = broadcaster
                    self.connection = connection
                    self.content_type = "text/event-stream"
                    self.set_header("Cache-Control", "no-cache")
                    self.set_header("Connection", "keep-alive")
                    self.set_header("Access-Control-Allow-Origin", "*")
                    self.set_header("Access-Control-Allow-Credentials", "true")
                
                def set_content(self, content):
                    pass  # Streaming response doesn't use set_content
                
                def set_json(self, data):
                    pass  # Not applicable for SSE
                
                def set_html(self, html):
                    pass  # Not applicable for SSE
                
                def set_text(self, text):
                    pass  # Not applicable for SSE
                
                def set_redirect(self, url, status_code=302):
                    pass  # Not applicable for SSE
                
                def set_stream(self, generator):
                    pass  # Already streaming
                
                def set_sse_response(self, data):
                    pass  # Already SSE
                
                def set_datastar_response(self, signals, fragments=None):
                    pass  # Handled by formatter
            
            response = SSEStreamingResponse(self.broadcaster, connection)
            
            # Set streaming generator
            response._streaming_generator = self.broadcaster.get_connection_stream(connection)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling SSE connection: {e}")
            
            # Return error response
            from ...infrastructure.web.interfaces import WebResponse
            
            class ErrorResponse(WebResponse):
                def __init__(self, error_message):
                    super().__init__()
                    self.status_code = 500
                    self._error_message = error_message
                
                def set_content(self, content):
                    self._content = str(content).encode('utf-8')
                
                def set_json(self, data):
                    self._content = json.dumps(data).encode('utf-8')
                    self.content_type = "application/json"
                
                def set_html(self, html):
                    self._content = html.encode('utf-8')
                    self.content_type = "text/html"
                
                def set_text(self, text):
                    self._content = text.encode('utf-8')
                    self.content_type = "text/plain"
                
                def set_redirect(self, url, status_code=302):
                    self.status_code = status_code
                    self.set_header('Location', url)
                
                def set_stream(self, generator):
                    pass  # Not applicable for error
                
                def set_sse_response(self, data):
                    pass  # Not applicable for error
                
                def set_datastar_response(self, signals, fragments=None):
                    pass  # Not applicable for error
            
            error_response = ErrorResponse(str(e))
            error_response.set_json({"error": str(e), "type": "connection_error"})
            return error_response

# Export main components
__all__ = [
    "SSEBroadcaster", "SSEBroadcastHandler", "ClientConnection", "ConnectionState"
]