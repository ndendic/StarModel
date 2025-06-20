"""
Protocol Manager - Unified Real-time Protocol Management

⚡ Protocol Abstraction and Management:
This module provides a unified interface for managing different real-time
communication protocols, enabling the application to switch between SSE,
WebSockets, and other protocols seamlessly.

Key Features:
- Protocol capability negotiation
- Automatic protocol selection based on client capabilities
- Unified API for all real-time protocols
- Extensible plugin system for new protocols
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, AsyncIterator, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

from ...events.streaming.event_bus import EventBus, DomainEvent, EventFilter
from ...infrastructure.web.interfaces import WebRequest, WebResponse
from .response_formatters import ResponseFormatter, FormatterContext, get_formatter_registry

logger = logging.getLogger(__name__)

class ProtocolType(Enum):
    """Supported real-time protocol types"""
    SSE = "sse"
    WEBSOCKET = "websocket"
    LONG_POLLING = "long_polling"
    GRPC_STREAMING = "grpc_streaming"

@dataclass
class ProtocolCapabilities:
    """Protocol capability descriptor"""
    protocol_type: ProtocolType
    bidirectional: bool = False
    supports_binary: bool = False
    supports_compression: bool = False
    supports_multiplexing: bool = False
    max_message_size: Optional[int] = None
    supported_content_types: List[str] = field(default_factory=list)
    required_headers: List[str] = field(default_factory=list)
    client_requirements: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default capabilities"""
        if not self.supported_content_types:
            if self.protocol_type == ProtocolType.SSE:
                self.supported_content_types = ["text/event-stream"]
            elif self.protocol_type == ProtocolType.WEBSOCKET:
                self.supported_content_types = ["application/json", "text/plain"]
            elif self.protocol_type == ProtocolType.LONG_POLLING:
                self.supported_content_types = ["application/json", "text/html"]
            elif self.protocol_type == ProtocolType.GRPC_STREAMING:
                self.supported_content_types = ["application/grpc", "application/grpc+proto"]

@dataclass
class ProtocolConnection:
    """Abstract protocol connection"""
    id: str
    protocol_type: ProtocolType
    request: WebRequest
    capabilities: ProtocolCapabilities
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

class ProtocolAdapter(ABC):
    """
    Abstract protocol adapter interface.
    
    Defines the contract for implementing different real-time
    communication protocols within the StarModel framework.
    """
    
    @abstractmethod
    def get_capabilities(self) -> ProtocolCapabilities:
        """Get protocol capabilities"""
        pass
    
    @abstractmethod
    def can_handle_request(self, request: WebRequest) -> bool:
        """Check if this adapter can handle the request"""
        pass
    
    @abstractmethod
    async def create_connection(self, request: WebRequest) -> ProtocolConnection:
        """Create a new protocol connection"""
        pass
    
    @abstractmethod
    async def handle_connection(self, connection: ProtocolConnection) -> WebResponse:
        """Handle the protocol connection and return response"""
        pass
    
    @abstractmethod
    async def send_event(self, connection: ProtocolConnection, event: DomainEvent):
        """Send event through the protocol connection"""
        pass
    
    @abstractmethod
    async def close_connection(self, connection: ProtocolConnection):
        """Close the protocol connection"""
        pass
    
    @abstractmethod
    def get_formatter(self) -> ResponseFormatter:
        """Get the response formatter for this protocol"""
        pass

class SSEProtocolAdapter(ProtocolAdapter):
    """Server-Sent Events protocol adapter"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.formatter = get_formatter_registry().get("datastar-sse")
        self._connections: Dict[str, ProtocolConnection] = {}
    
    def get_capabilities(self) -> ProtocolCapabilities:
        """Get SSE protocol capabilities"""
        return ProtocolCapabilities(
            protocol_type=ProtocolType.SSE,
            bidirectional=False,
            supports_binary=False,
            supports_compression=True,
            supports_multiplexing=False,
            supported_content_types=["text/event-stream"],
            required_headers=["Accept: text/event-stream"],
            client_requirements={"javascript": True}
        )
    
    def can_handle_request(self, request: WebRequest) -> bool:
        """Check if request wants SSE"""
        accept_header = request.headers.get('accept', '')
        return 'text/event-stream' in accept_header
    
    async def create_connection(self, request: WebRequest) -> ProtocolConnection:
        """Create SSE connection"""
        connection_id = f"sse_{datetime.now().timestamp()}"
        
        connection = ProtocolConnection(
            id=connection_id,
            protocol_type=ProtocolType.SSE,
            request=request,
            capabilities=self.get_capabilities(),
            user_id=request.get_user(),
            session_id=request.get_session().get('session_id') if request.get_session() else None
        )
        
        self._connections[connection_id] = connection
        return connection
    
    async def handle_connection(self, connection: ProtocolConnection) -> WebResponse:
        """Handle SSE connection"""
        from ...infrastructure.web.interfaces import WebResponse
        
        class SSEResponse(WebResponse):
            def __init__(self, adapter, connection):
                super().__init__()
                self.adapter = adapter
                self.connection = connection
                self.content_type = "text/event-stream"
                self.set_header("Cache-Control", "no-cache")
                self.set_header("Connection", "keep-alive")
                self.set_header("Access-Control-Allow-Origin", "*")
            
            def set_content(self, content):
                pass
            def set_json(self, data):
                pass
            def set_html(self, html):
                pass
            def set_text(self, text):
                pass
            def set_redirect(self, url, status_code=302):
                pass
            def set_stream(self, generator):
                pass
            def set_sse_response(self, data):
                pass
            def set_datastar_response(self, signals, fragments=None):
                pass
        
        response = SSEResponse(self, connection)
        response._streaming_generator = self._create_event_stream(connection)
        return response
    
    async def _create_event_stream(self, connection: ProtocolConnection) -> AsyncIterator[str]:
        """Create SSE event stream"""
        try:
            # Send connection established event
            yield f"event: connection\n"
            yield f"data: {json.dumps({'type': 'connected', 'connection_id': connection.id})}\n\n"
            
            # Subscribe to events
            event_queue = asyncio.Queue()
            
            async def event_handler(event: DomainEvent):
                await event_queue.put(event)
            
            subscription_id = await self.event_bus.subscribe(event_handler)
            
            try:
                while True:
                    try:
                        # Wait for event with timeout
                        event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                        
                        # Format and send event
                        yield f"event: {event.event_type}\n"
                        yield f"data: {json.dumps({'type': event.event_type, 'data': event.data})}\n\n"
                        
                        connection.update_activity()
                        
                    except asyncio.TimeoutError:
                        # Send heartbeat
                        yield f"event: heartbeat\n"
                        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                        connection.update_activity()
            
            finally:
                await self.event_bus.unsubscribe(subscription_id)
        
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            yield f"event: error\n"
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        finally:
            await self.close_connection(connection)
    
    async def send_event(self, connection: ProtocolConnection, event: DomainEvent):
        """Send event to SSE connection"""
        # Events are sent through the stream in _create_event_stream
        pass
    
    async def close_connection(self, connection: ProtocolConnection):
        """Close SSE connection"""
        if connection.id in self._connections:
            del self._connections[connection.id]
    
    def get_formatter(self) -> ResponseFormatter:
        """Get SSE formatter"""
        return self.formatter

class WebSocketProtocolAdapter(ProtocolAdapter):
    """WebSocket protocol adapter"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.formatter = get_formatter_registry().get("websocket")
        self._connections: Dict[str, ProtocolConnection] = {}
    
    def get_capabilities(self) -> ProtocolCapabilities:
        """Get WebSocket protocol capabilities"""
        return ProtocolCapabilities(
            protocol_type=ProtocolType.WEBSOCKET,
            bidirectional=True,
            supports_binary=True,
            supports_compression=True,
            supports_multiplexing=True,
            supported_content_types=["application/json", "text/plain"],
            required_headers=["Upgrade: websocket", "Connection: Upgrade"],
            client_requirements={"websocket": True}
        )
    
    def can_handle_request(self, request: WebRequest) -> bool:
        """Check if request wants WebSocket"""
        upgrade_header = request.headers.get('upgrade', '').lower()
        connection_header = request.headers.get('connection', '').lower()
        return upgrade_header == 'websocket' and 'upgrade' in connection_header
    
    async def create_connection(self, request: WebRequest) -> ProtocolConnection:
        """Create WebSocket connection"""
        connection_id = f"ws_{datetime.now().timestamp()}"
        
        connection = ProtocolConnection(
            id=connection_id,
            protocol_type=ProtocolType.WEBSOCKET,
            request=request,
            capabilities=self.get_capabilities(),
            user_id=request.get_user(),
            session_id=request.get_session().get('session_id') if request.get_session() else None
        )
        
        self._connections[connection_id] = connection
        return connection
    
    async def handle_connection(self, connection: ProtocolConnection) -> WebResponse:
        """Handle WebSocket connection"""
        # WebSocket handling would typically be done by the web framework
        # This is a placeholder implementation
        from ...infrastructure.web.interfaces import WebResponse
        
        class WebSocketResponse(WebResponse):
            def __init__(self, adapter, connection):
                super().__init__()
                self.adapter = adapter
                self.connection = connection
                self.status_code = 101  # Switching Protocols
                self.set_header("Upgrade", "websocket")
                self.set_header("Connection", "Upgrade")
            
            def set_content(self, content):
                pass
            def set_json(self, data):
                pass
            def set_html(self, html):
                pass
            def set_text(self, text):
                pass
            def set_redirect(self, url, status_code=302):
                pass
            def set_stream(self, generator):
                pass
            def set_sse_response(self, data):
                pass
            def set_datastar_response(self, signals, fragments=None):
                pass
        
        return WebSocketResponse(self, connection)
    
    async def send_event(self, connection: ProtocolConnection, event: DomainEvent):
        """Send event to WebSocket connection"""
        # Implementation would depend on WebSocket framework
        pass
    
    async def close_connection(self, connection: ProtocolConnection):
        """Close WebSocket connection"""
        if connection.id in self._connections:
            del self._connections[connection.id]
    
    def get_formatter(self) -> ResponseFormatter:
        """Get WebSocket formatter"""
        return self.formatter

class LongPollingProtocolAdapter(ProtocolAdapter):
    """HTTP Long Polling protocol adapter"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.formatter = get_formatter_registry().get("json")
        self._connections: Dict[str, ProtocolConnection] = {}
    
    def get_capabilities(self) -> ProtocolCapabilities:
        """Get Long Polling protocol capabilities"""
        return ProtocolCapabilities(
            protocol_type=ProtocolType.LONG_POLLING,
            bidirectional=False,
            supports_binary=False,
            supports_compression=True,
            supports_multiplexing=False,
            supported_content_types=["application/json", "text/html"],
            required_headers=[],
            client_requirements={}
        )
    
    def can_handle_request(self, request: WebRequest) -> bool:
        """Check if request wants long polling"""
        # Long polling is often indicated by specific query parameters
        return request.query_params.get('long_poll') == 'true'
    
    async def create_connection(self, request: WebRequest) -> ProtocolConnection:
        """Create long polling connection"""
        connection_id = f"lp_{datetime.now().timestamp()}"
        
        connection = ProtocolConnection(
            id=connection_id,
            protocol_type=ProtocolType.LONG_POLLING,
            request=request,
            capabilities=self.get_capabilities(),
            user_id=request.get_user(),
            session_id=request.get_session().get('session_id') if request.get_session() else None
        )
        
        self._connections[connection_id] = connection
        return connection
    
    async def handle_connection(self, connection: ProtocolConnection) -> WebResponse:
        """Handle long polling connection"""
        # Wait for events with timeout
        event_queue = asyncio.Queue()
        
        async def event_handler(event: DomainEvent):
            await event_queue.put(event)
        
        subscription_id = await self.event_bus.subscribe(event_handler)
        
        try:
            # Wait for event or timeout
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                
                # Format event response
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
                
                formatter_context = FormatterContext(
                    request=connection.request,
                    user_id=connection.user_id,
                    session_id=connection.session_id
                )
                
                return await self.formatter.format_response(command_result, formatter_context)
                
            except asyncio.TimeoutError:
                # Return timeout response
                from ...infrastructure.web.interfaces import WebResponse
                
                class TimeoutResponse(WebResponse):
                    def __init__(self):
                        super().__init__()
                        self.status_code = 204  # No Content
                    
                    def set_content(self, content):
                        pass
                    def set_json(self, data):
                        pass
                    def set_html(self, html):
                        pass
                    def set_text(self, text):
                        pass
                    def set_redirect(self, url, status_code=302):
                        pass
                    def set_stream(self, generator):
                        pass
                    def set_sse_response(self, data):
                        pass
                    def set_datastar_response(self, signals, fragments=None):
                        pass
                
                return TimeoutResponse()
        
        finally:
            await self.event_bus.unsubscribe(subscription_id)
            await self.close_connection(connection)
    
    async def send_event(self, connection: ProtocolConnection, event: DomainEvent):
        """Send event to long polling connection"""
        # Events are sent through the handle_connection method
        pass
    
    async def close_connection(self, connection: ProtocolConnection):
        """Close long polling connection"""
        if connection.id in self._connections:
            del self._connections[connection.id]
    
    def get_formatter(self) -> ResponseFormatter:
        """Get long polling formatter"""
        return self.formatter

class ProtocolManager:
    """
    Protocol manager for unified real-time communication.
    
    Manages multiple protocol adapters and provides automatic
    protocol selection based on client capabilities and preferences.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._adapters: Dict[ProtocolType, ProtocolAdapter] = {}
        self._connections: Dict[str, ProtocolConnection] = {}
        self._connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'connections_by_protocol': {}
        }
        
        # Register default adapters
        self._register_default_adapters()
    
    def _register_default_adapters(self):
        """Register default protocol adapters"""
        self.register_adapter(SSEProtocolAdapter(self.event_bus))
        self.register_adapter(WebSocketProtocolAdapter(self.event_bus))
        self.register_adapter(LongPollingProtocolAdapter(self.event_bus))
    
    def register_adapter(self, adapter: ProtocolAdapter):
        """Register a protocol adapter"""
        protocol_type = adapter.get_capabilities().protocol_type
        self._adapters[protocol_type] = adapter
        self._connection_stats['connections_by_protocol'][protocol_type.value] = 0
        logger.info(f"Registered protocol adapter: {protocol_type.value}")
    
    def get_adapter(self, protocol_type: ProtocolType) -> Optional[ProtocolAdapter]:
        """Get adapter for protocol type"""
        return self._adapters.get(protocol_type)
    
    def select_protocol(self, request: WebRequest) -> Optional[ProtocolAdapter]:
        """Select best protocol adapter for request"""
        # Check each adapter to see if it can handle the request
        for adapter in self._adapters.values():
            if adapter.can_handle_request(request):
                return adapter
        
        # Default to SSE if available
        return self._adapters.get(ProtocolType.SSE)
    
    async def handle_connection(self, request: WebRequest) -> WebResponse:
        """Handle incoming connection request"""
        # Select appropriate protocol
        adapter = self.select_protocol(request)
        if not adapter:
            # Return error response
            from ...infrastructure.web.interfaces import WebResponse
            
            class ErrorResponse(WebResponse):
                def __init__(self, message):
                    super().__init__()
                    self.status_code = 400
                    self._message = message
                
                def set_content(self, content):
                    self._content = str(content).encode('utf-8')
                def set_json(self, data):
                    self._content = json.dumps(data).encode('utf-8')
                    self.content_type = "application/json"
                def set_html(self, html):
                    self._content = html.encode('utf-8')
                def set_text(self, text):
                    self._content = text.encode('utf-8')
                def set_redirect(self, url, status_code=302):
                    pass
                def set_stream(self, generator):
                    pass
                def set_sse_response(self, data):
                    pass
                def set_datastar_response(self, signals, fragments=None):
                    pass
            
            error_response = ErrorResponse("No suitable protocol adapter found")
            error_response.set_json({"error": "No suitable protocol adapter found"})
            return error_response
        
        # Create connection
        connection = await adapter.create_connection(request)
        self._connections[connection.id] = connection
        
        # Update stats
        self._connection_stats['total_connections'] += 1
        self._connection_stats['active_connections'] += 1
        self._connection_stats['connections_by_protocol'][connection.protocol_type.value] += 1
        
        # Handle connection
        return await adapter.handle_connection(connection)
    
    async def broadcast_event(self, event: DomainEvent, filter_func: Optional[Callable[[ProtocolConnection], bool]] = None):
        """Broadcast event to all matching connections"""
        for connection in self._connections.values():
            if filter_func is None or filter_func(connection):
                adapter = self._adapters.get(connection.protocol_type)
                if adapter:
                    try:
                        await adapter.send_event(connection, event)
                    except Exception as e:
                        logger.error(f"Error sending event to connection {connection.id}: {e}")
    
    async def close_connection(self, connection_id: str):
        """Close a specific connection"""
        connection = self._connections.get(connection_id)
        if connection:
            adapter = self._adapters.get(connection.protocol_type)
            if adapter:
                await adapter.close_connection(connection)
            
            del self._connections[connection_id]
            self._connection_stats['active_connections'] -= 1
    
    def get_capabilities(self) -> Dict[ProtocolType, ProtocolCapabilities]:
        """Get capabilities for all registered protocols"""
        return {
            protocol_type: adapter.get_capabilities()
            for protocol_type, adapter in self._adapters.items()
        }
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            **self._connection_stats,
            'supported_protocols': list(self._adapters.keys())
        }

# Export main components
__all__ = [
    "ProtocolManager", "ProtocolAdapter", "ProtocolCapabilities", "ProtocolConnection",
    "ProtocolType", "SSEProtocolAdapter", "WebSocketProtocolAdapter", "LongPollingProtocolAdapter"
]