"""
Web Integration Layer - Framework-Agnostic Web Setup

🌐 Clean Web Architecture Integration:
This module provides the main integration layer for web frameworks,
coordinating between adapters, route generation, and dependency injection
while maintaining clean architecture separation.
"""

from typing import List, Type, Optional, Dict, Any, Callable
import asyncio
from dataclasses import dataclass, field

from .interfaces import WebAdapter, HttpMethod, RouteHandler
from .routing import RouteRegistry, Route
from .generators import EntityRouteGenerator, EntityRouteConfig
from .session import SessionManager, SessionConfig
from ..infrastructure.dependency_injection import DIContainer, get_current_container

# Forward reference to Entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..entities.lifecycle.entity import Entity

@dataclass
class WebIntegrationConfig:
    """Configuration for web integration"""
    # Route configuration
    auto_register_entities: bool = True
    enable_crud_routes: bool = True
    enable_event_routes: bool = True
    base_route_path: str = "/entities"
    
    # Session configuration
    enable_sessions: bool = True
    session_config: Optional[SessionConfig] = None
    
    # Security configuration
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    enable_csrf: bool = False
    
    # Performance configuration
    enable_compression: bool = True
    enable_caching: bool = True
    
    # Error handling
    enable_error_pages: bool = True
    debug_mode: bool = False

class WebIntegration:
    """
    Main web integration coordinator.
    
    Coordinates between web adapters, route generation, dependency injection,
    and entity management to provide complete web framework integration.
    """
    
    def __init__(self, adapter: WebAdapter, config: Optional[WebIntegrationConfig] = None):
        self.adapter = adapter
        self.config = config or WebIntegrationConfig()
        self.route_registry = RouteRegistry()
        self.entity_route_generator = None
        self.session_manager = None
        self.container: Optional[DIContainer] = None
        self._is_configured = False
        self._registered_entities: List[Type['Entity']] = []
    
    async def configure(self, container: Optional[DIContainer] = None) -> 'WebIntegration':
        """Configure web integration with dependency injection"""
        if self._is_configured:
            return self
        
        # Set up DI container
        self.container = container or get_current_container()
        
        # Configure session management
        if self.config.enable_sessions:
            await self._configure_sessions()
        
        # Configure route generation
        await self._configure_route_generation()
        
        # Configure middleware
        await self._configure_middleware()
        
        # Configure error handling
        await self._configure_error_handling()
        
        self._is_configured = True
        return self
    
    async def _configure_sessions(self):
        """Configure session management"""
        session_config = self.config.session_config or SessionConfig()
        self.session_manager = SessionManager(session_config)
        
        # Register session manager with DI container
        if self.container:
            self.container.register_singleton("SessionManager", lambda: self.session_manager)
    
    async def _configure_route_generation(self):
        """Configure automatic route generation"""
        # Create entity route generator
        entity_config = EntityRouteConfig(
            base_path=self.config.base_route_path,
            enable_crud=self.config.enable_crud_routes,
            enable_events=self.config.enable_event_routes,
            auto_register=False  # We'll register manually
        )
        
        self.entity_route_generator = EntityRouteGenerator(self.route_registry, entity_config)
    
    async def _configure_middleware(self):
        """Configure web middleware"""
        # Session middleware
        if self.session_manager:
            from .session import SessionMiddleware
            session_middleware = SessionMiddleware(self.session_manager)
            self.adapter.register_middleware(session_middleware)
        
        # CORS middleware
        if self.config.enable_cors:
            cors_middleware = self._create_cors_middleware()
            self.adapter.register_middleware(cors_middleware)
        
        # Compression middleware
        if self.config.enable_compression:
            compression_middleware = self._create_compression_middleware()
            if compression_middleware:
                self.adapter.register_middleware(compression_middleware)
    
    async def _configure_error_handling(self):
        """Configure error handling"""
        if self.config.enable_error_pages:
            # Register error handlers
            self.adapter.add_exception_handler(404, self._handle_404)
            self.adapter.add_exception_handler(500, self._handle_500)
            self.adapter.add_exception_handler(Exception, self._handle_generic_error)
    
    def register_entity(self, entity_class: Type['Entity']) -> 'WebIntegration':
        """Register an entity for automatic route generation"""
        if entity_class not in self._registered_entities:
            self._registered_entities.append(entity_class)
            
            if self.config.auto_register_entities and self.entity_route_generator:
                # Generate and register routes
                routes = self.entity_route_generator.generate_entity_routes(entity_class)
                self._register_routes(routes)
        
        return self
    
    def register_entities(self, entity_classes: List[Type['Entity']]) -> 'WebIntegration':
        """Register multiple entities for automatic route generation"""
        for entity_class in entity_classes:
            self.register_entity(entity_class)
        return self
    
    def register_route(self, method: HttpMethod, path: str, handler) -> 'WebIntegration':
        """Register a custom route"""
        from .routing import FunctionRouteHandler
        
        # Convert function to route handler if needed
        if not isinstance(handler, RouteHandler):
            route_handler = FunctionRouteHandler(handler)
        else:
            route_handler = handler
        
        # Register with adapter
        self.adapter.register_route(method, path, route_handler)
        
        return self
    
    def _register_routes(self, routes: List[Route]):
        """Register routes with the web adapter"""
        for route in routes:
            # Convert RouteMethod to HttpMethod
            http_method = HttpMethod(route.method.value)
            self.adapter.register_route(http_method, route.path, route.handler)
    
    def add_middleware(self, middleware: Callable) -> 'WebIntegration':
        """Add custom middleware"""
        self.adapter.register_middleware(middleware)
        return self
    
    def add_static_files(self, path: str, directory: str) -> 'WebIntegration':
        """Add static file serving"""
        if hasattr(self.adapter, 'register_static_files'):
            self.adapter.register_static_files(path, directory)
        return self
    
    # Middleware creation helpers
    def _create_cors_middleware(self) -> Optional[Callable]:
        """Create CORS middleware based on adapter type"""
        # This would be adapter-specific
        if hasattr(self.adapter, 'app') and hasattr(self.adapter.app, 'add_middleware'):
            try:
                from starlette.middleware.cors import CORSMiddleware
                
                def add_cors():
                    self.adapter.app.add_middleware(
                        CORSMiddleware,
                        allow_origins=self.config.cors_origins,
                        allow_credentials=True,
                        allow_methods=["*"],
                        allow_headers=["*"]
                    )
                
                return add_cors
            except ImportError:
                pass
        
        return None
    
    def _create_compression_middleware(self) -> Optional[Callable]:
        """Create compression middleware based on adapter type"""
        if hasattr(self.adapter, 'app') and hasattr(self.adapter.app, 'add_middleware'):
            try:
                from starlette.middleware.gzip import GZipMiddleware
                
                def add_gzip():
                    self.adapter.app.add_middleware(GZipMiddleware, minimum_size=1000)
                
                return add_gzip
            except ImportError:
                pass
        
        return None
    
    # Error handlers
    async def _handle_404(self, request, exc):
        """Handle 404 errors"""
        if self.config.debug_mode:
            return {"error": "Not Found", "path": request.url.path}
        else:
            return "Page not found"
    
    async def _handle_500(self, request, exc):
        """Handle 500 errors"""
        if self.config.debug_mode:
            import traceback
            return {
                "error": "Internal Server Error",
                "details": str(exc),
                "traceback": traceback.format_exc()
            }
        else:
            return "Internal server error"
    
    async def _handle_generic_error(self, request, exc):
        """Handle generic errors"""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unhandled error in web request: {exc}")
        
        if self.config.debug_mode:
            return {"error": str(exc), "type": exc.__class__.__name__}
        else:
            return "An error occurred"
    
    # Startup and lifecycle
    async def startup(self):
        """Startup web integration"""
        if not self._is_configured:
            await self.configure()
        
        # Start session cleanup if enabled
        if self.session_manager:
            # Could start background cleanup task here
            pass
    
    async def shutdown(self):
        """Shutdown web integration"""
        if self.session_manager:
            # Could stop background tasks here
            pass
    
    def start_server(self, host: str = "localhost", port: int = 8000):
        """Start the web server"""
        # Ensure configuration is complete
        if not self._is_configured:
            asyncio.run(self.configure())
        
        self.adapter.start_server(host, port)
    
    def get_registered_entities(self) -> List[Type['Entity']]:
        """Get list of registered entities"""
        return self._registered_entities.copy()
    
    def get_routes(self) -> List[Route]:
        """Get all registered routes"""
        return self.route_registry.get_all_routes()
    
    def get_entity_routes(self, entity_class: Type['Entity']) -> List[Route]:
        """Get routes for a specific entity"""
        if self.entity_route_generator:
            return self.entity_route_generator.get_entity_routes(entity_class)
        return []

class WebIntegrationBuilder:
    """
    Builder for creating web integration configurations.
    
    Provides a fluent interface for configuring web integration
    with various options and settings.
    """
    
    def __init__(self, adapter: WebAdapter):
        self.adapter = adapter
        self.config = WebIntegrationConfig()
        self.entities: List[Type['Entity']] = []
        self.custom_routes: List[tuple] = []
        self.middleware_list: List[Callable] = []
    
    def with_entities(self, *entity_classes: Type['Entity']) -> 'WebIntegrationBuilder':
        """Add entities to the integration"""
        self.entities.extend(entity_classes)
        return self
    
    def with_base_path(self, path: str) -> 'WebIntegrationBuilder':
        """Set base path for entity routes"""
        self.config.base_route_path = path
        return self
    
    def with_sessions(self, session_config: Optional[SessionConfig] = None) -> 'WebIntegrationBuilder':
        """Enable sessions with optional configuration"""
        self.config.enable_sessions = True
        if session_config:
            self.config.session_config = session_config
        return self
    
    def without_sessions(self) -> 'WebIntegrationBuilder':
        """Disable sessions"""
        self.config.enable_sessions = False
        return self
    
    def with_cors(self, origins: List[str] = None) -> 'WebIntegrationBuilder':
        """Enable CORS with optional origins"""
        self.config.enable_cors = True
        if origins:
            self.config.cors_origins = origins
        return self
    
    def without_cors(self) -> 'WebIntegrationBuilder':
        """Disable CORS"""
        self.config.enable_cors = False
        return self
    
    def debug_mode(self, enabled: bool = True) -> 'WebIntegrationBuilder':
        """Set debug mode"""
        self.config.debug_mode = enabled
        return self
    
    def with_route(self, method: HttpMethod, path: str, handler) -> 'WebIntegrationBuilder':
        """Add a custom route"""
        self.custom_routes.append((method, path, handler))
        return self
    
    def with_middleware(self, middleware: Callable) -> 'WebIntegrationBuilder':
        """Add middleware"""
        self.middleware_list.append(middleware)
        return self
    
    def with_static_files(self, path: str, directory: str) -> 'WebIntegrationBuilder':
        """Add static file serving"""
        # Store for later application
        if not hasattr(self, '_static_files'):
            self._static_files = []
        self._static_files.append((path, directory))
        return self
    
    async def build(self, container: Optional[DIContainer] = None) -> WebIntegration:
        """Build the web integration"""
        integration = WebIntegration(self.adapter, self.config)
        
        # Configure
        await integration.configure(container)
        
        # Register entities
        if self.entities:
            integration.register_entities(self.entities)
        
        # Add custom routes
        for method, path, handler in self.custom_routes:
            integration.register_route(method, path, handler)
        
        # Add middleware
        for middleware in self.middleware_list:
            integration.add_middleware(middleware)
        
        # Add static files
        if hasattr(self, '_static_files'):
            for path, directory in self._static_files:
                integration.add_static_files(path, directory)
        
        return integration

# Convenience functions
async def create_web_integration(
    adapter: WebAdapter,
    entities: List[Type['Entity']] = None,
    config: Optional[WebIntegrationConfig] = None,
    container: Optional[DIContainer] = None
) -> WebIntegration:
    """Create and configure web integration"""
    integration = WebIntegration(adapter, config)
    await integration.configure(container)
    
    if entities:
        integration.register_entities(entities)
    
    return integration

def web_integration_builder(adapter: WebAdapter) -> WebIntegrationBuilder:
    """Create a web integration builder"""
    return WebIntegrationBuilder(adapter)

# Export main components
__all__ = [
    "WebIntegration", "WebIntegrationConfig", "WebIntegrationBuilder",
    "create_web_integration", "web_integration_builder"
]