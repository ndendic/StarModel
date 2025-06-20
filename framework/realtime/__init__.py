"""
Real-time Module - Live Interactions and Reactive Updates

⚡ StarModel Real-time Capabilities:
This module provides comprehensive real-time functionality for StarModel,
enabling live interactions, reactive state synchronization, and event-driven
UI updates across different communication protocols.

Core Components:
- Broadcasting: Event distribution to connected clients
- Protocols: Pluggable real-time communication mechanisms  
- Synchronization: State sync across clients and sessions
- Connections: Client connection management

Supported Protocols:
- Server-Sent Events (SSE) with Datastar integration
- WebSockets for bidirectional communication
- HTTP Long Polling for legacy support

Key Features:
- Protocol abstraction for pluggable real-time mechanisms
- Event bus integration for domain event broadcasting
- Client connection management with automatic cleanup
- Response formatters for different output formats
- Real-time state synchronization
"""

# Broadcasting components
try:
    from .broadcasting.sse_broadcaster import (
        SSEBroadcaster, SSEBroadcastHandler, ClientConnection, ConnectionState
    )
except ImportError:
    SSEBroadcaster = None
    SSEBroadcastHandler = None
    ClientConnection = None
    ConnectionState = None

# Protocol components
try:
    from .protocols import (
        ResponseFormatter, FormatterContext, FormatterRegistry,
        DatastarSSEFormatter, JSONResponseFormatter, WebSocketFormatter, HTMLTemplateFormatter,
        get_formatter_registry, get_formatter,
        ProtocolManager, ProtocolAdapter, ProtocolCapabilities,
        SSEProtocolAdapter, WebSocketProtocolAdapter, LongPollingProtocolAdapter
    )
except ImportError:
    ResponseFormatter = None
    FormatterContext = None
    FormatterRegistry = None
    DatastarSSEFormatter = None
    JSONResponseFormatter = None
    WebSocketFormatter = None
    HTMLTemplateFormatter = None
    get_formatter_registry = None
    get_formatter = None
    ProtocolManager = None
    ProtocolAdapter = None
    ProtocolCapabilities = None
    SSEProtocolAdapter = None
    WebSocketProtocolAdapter = None
    LongPollingProtocolAdapter = None

# Legacy compatibility placeholders
try:
    from .synchronization.state_sync import StateSynchronizer
except ImportError:
    StateSynchronizer = None

def enable_collaboration(app, **config):
    """Enable real-time collaboration features"""
    # Placeholder implementation
    pass

def configure_realtime(protocol="sse", **config):
    """Configure real-time communication protocol"""
    # Placeholder implementation
    pass

# Export main components
__all__ = [
    # Broadcasting
    "SSEBroadcaster", "SSEBroadcastHandler", "ClientConnection", "ConnectionState",
    
    # Protocols and formatting
    "ResponseFormatter", "FormatterContext", "FormatterRegistry",
    "DatastarSSEFormatter", "JSONResponseFormatter", "WebSocketFormatter", "HTMLTemplateFormatter",
    "get_formatter_registry", "get_formatter",
    "ProtocolManager", "ProtocolAdapter", "ProtocolCapabilities",
    "SSEProtocolAdapter", "WebSocketProtocolAdapter", "LongPollingProtocolAdapter",
    
    # Legacy compatibility
    "StateSynchronizer", "enable_collaboration", "configure_realtime"
]