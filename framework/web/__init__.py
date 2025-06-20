"""
Web Layer - Framework-Agnostic Web Integration

🌐 Clean Web Architecture:
This module provides web framework abstraction for StarModel applications,
enabling clean separation between domain logic and web infrastructure.

Components:
- WebRequest/WebResponse abstractions
- Framework adapters (FastHTML, FastAPI, etc.)
- Route management and registration
- Request/response handling
- Session and authentication integration
"""

from .interfaces import (
    WebRequest, WebResponse, WebAdapter, RouteHandler, WebContext,
    HttpMethod, ContentType, WebCookie, WebFile, ResponseBuilder
)
from .routing import RouteRegistry, Route, RouteMethod, EntityRouteBuilder
from .session import SessionManager, SessionData, SessionConfig
from .integration import (
    WebIntegration, WebIntegrationConfig, WebIntegrationBuilder,
    create_web_integration, web_integration_builder
)
from .generators import EntityRouteGenerator, EventRouteHandler
from .adapters import FastHTMLAdapter, FastHTMLRequest, FastHTMLResponse

__all__ = [
    # Core interfaces
    "WebRequest", "WebResponse", "WebAdapter", "RouteHandler", "WebContext",
    "HttpMethod", "ContentType", "WebCookie", "WebFile", "ResponseBuilder",
    
    # Routing
    "RouteRegistry", "Route", "RouteMethod", "EntityRouteBuilder",
    
    # Session management
    "SessionManager", "SessionData", "SessionConfig",
    
    # Integration
    "WebIntegration", "WebIntegrationConfig", "WebIntegrationBuilder",
    "create_web_integration", "web_integration_builder",
    
    # Route generation
    "EntityRouteGenerator", "EventRouteHandler",
    
    # Adapters
    "FastHTMLAdapter", "FastHTMLRequest", "FastHTMLResponse"
]