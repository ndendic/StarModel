"""
Real-time Protocols - Unified Real-time Communication Abstractions

⚡ Protocol Abstraction Layer:
This module provides unified abstractions for different real-time communication
protocols, enabling pluggable real-time mechanisms while maintaining a consistent
API for the application layer.

Supported Protocols:
- Server-Sent Events (SSE) with Datastar integration
- WebSockets for bidirectional communication
- HTTP Long Polling for legacy support
- gRPC Streaming for high-performance scenarios
"""

from .response_formatters import (
    ResponseFormatter, FormatterContext, FormatterRegistry,
    DatastarSSEFormatter, JSONResponseFormatter, WebSocketFormatter, HTMLTemplateFormatter,
    get_formatter_registry, get_formatter
)

from .protocol_manager import (
    ProtocolManager, ProtocolAdapter, ProtocolCapabilities,
    SSEProtocolAdapter, WebSocketProtocolAdapter, LongPollingProtocolAdapter
)

# Export main components
__all__ = [
    # Response formatters
    "ResponseFormatter", "FormatterContext", "FormatterRegistry",
    "DatastarSSEFormatter", "JSONResponseFormatter", "WebSocketFormatter", "HTMLTemplateFormatter",
    "get_formatter_registry", "get_formatter",
    
    # Protocol management
    "ProtocolManager", "ProtocolAdapter", "ProtocolCapabilities",
    "SSEProtocolAdapter", "WebSocketProtocolAdapter", "LongPollingProtocolAdapter"
]