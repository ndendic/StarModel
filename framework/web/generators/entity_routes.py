"""
Entity Route Generator - Automatic Entity Route Creation

🎯 Clean Entity Web Integration:
This module generates web routes for StarModel entities, automatically
creating routes for entity events and operations while maintaining
clean separation between domain logic and web concerns.
"""

from typing import Dict, List, Optional, Type, Any, Callable
import inspect
import asyncio
from dataclasses import dataclass
from enum import Enum

from ..interfaces import WebRequest, WebResponse, RouteHandler, HttpMethod, ResponseBuilder
from ..routing import RouteRegistry, Route, RouteMethod, EntityRouteBuilder
from ...events.commands.event import EventMetadata
from ...entities.mixins.events import EventCapable

# Forward reference to Entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...entities.lifecycle.entity import Entity

class EventRouteType(Enum):
    """Types of event routes"""
    INSTANCE_EVENT = "instance"  # /entities/EntityName/{id}/events/eventName
    CLASS_EVENT = "class"        # /entities/EntityName/events/eventName
    CRUD_EVENT = "crud"          # /entities/EntityName, /entities/EntityName/{id}

@dataclass
class EntityRouteConfig:
    """Configuration for entity route generation"""
    base_path: str = "/entities"
    enable_crud: bool = True
    enable_events: bool = True
    enable_list: bool = True
    enable_detail: bool = True
    enable_create: bool = True
    enable_update: bool = True
    enable_delete: bool = True
    auto_register: bool = True
    require_authentication: bool = False
    custom_middleware: List[Callable] = None

class EventRouteHandler(RouteHandler):
    """Route handler for entity events"""
    
    def __init__(self, entity_class: Type['Entity'], event_name: str, 
                 event_type: EventRouteType = EventRouteType.INSTANCE_EVENT):
        self.entity_class = entity_class
        self.event_name = event_name
        self.event_type = event_type
    
    async def handle(self, request: WebRequest) -> WebResponse:
        """Handle entity event request"""
        response = ResponseBuilder()
        
        try:
            # Get event dispatcher from DI container
            dispatcher = self._get_event_dispatcher(request)
            if not dispatcher:
                return self._create_error_response("Event dispatcher not available", 500)
            
            # Extract entity ID if needed
            entity_id = None
            if self.event_type == EventRouteType.INSTANCE_EVENT:
                entity_id = request.get_entity_id(self.entity_class)
                if not entity_id:
                    return self._create_error_response("Entity ID required", 400)
            
            # Get entity instance
            entity = await self._get_entity_instance(entity_id, request)
            if not entity and self.event_type == EventRouteType.INSTANCE_EVENT:
                return self._create_error_response("Entity not found", 404)
            
            # Extract event parameters from request
            event_params = await self._extract_event_parameters(request)
            
            # Execute event through dispatcher
            from ...events.dispatching.command_context import CommandContext
            
            context = CommandContext(
                entity_class=self.entity_class,
                entity_id=entity_id,
                event_name=self.event_name,
                parameters=event_params,
                request=request
            )
            
            result = await dispatcher.dispatch(context)
            
            # Create response based on result
            if result.success:
                return await self._create_success_response(result, request)
            else:
                return self._create_error_response(result.error_message, 400)
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error handling entity event {self.event_name}: {e}")
            return self._create_error_response("Internal server error", 500)
    
    async def _get_entity_instance(self, entity_id: Optional[str], 
                                 request: WebRequest) -> Optional['Entity']:
        """Get entity instance from persistence"""
        if not entity_id:
            # For class events, create a new instance
            return self.entity_class()
        
        # Load entity from persistence
        try:
            persistence_manager = self._get_persistence_manager(request)
            if persistence_manager:
                repository = await persistence_manager.get_repository(self.entity_class)
                return await repository.load(self.entity_class, entity_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not load entity {entity_id}: {e}")
        
        return None
    
    async def _extract_event_parameters(self, request: WebRequest) -> Dict[str, Any]:
        """Extract event parameters from request"""
        params = {}
        
        # Get Datastar payload (contains signals and form data)
        datastar_payload = request.get_datastar_payload()
        params.update(datastar_payload)
        
        # Get query parameters
        params.update(request.query_params)
        
        # Get form data for POST requests
        if request.method == HttpMethod.POST:
            try:
                form_data = await request.form()
                params.update(form_data)
            except:
                pass
        
        # Get JSON data
        if request.content_type and 'json' in request.content_type:
            try:
                json_data = await request.json()
                params.update(json_data)
            except:
                pass
        
        return params
    
    async def _create_success_response(self, result, request: WebRequest) -> WebResponse:
        """Create success response from event result"""
        # Create response based on result type
        if hasattr(result, 'signals') and result.signals:
            # Return Datastar response with signals
            response = request.adapter.create_response() if hasattr(request, 'adapter') else None
            if response and hasattr(response, 'set_datastar_response'):
                response.set_datastar_response(result.signals, result.fragments if hasattr(result, 'fragments') else None)
                return response
        
        # Default to JSON response
        return self._create_json_response({"success": True, "result": str(result.result) if hasattr(result, 'result') else None})
    
    def _create_error_response(self, message: str, status_code: int) -> WebResponse:
        """Create error response"""
        return self._create_json_response({"error": message}, status_code)
    
    def _create_json_response(self, data: Dict[str, Any], status_code: int = 200) -> WebResponse:
        """Create JSON response"""
        # Create a generic response - adapter will handle the specifics
        from ..adapters.fasthtml import FastHTMLResponse
        response = FastHTMLResponse()  # This should be injected from adapter
        response.status_code = status_code
        response.set_json(data)
        return response
    
    def _get_event_dispatcher(self, request: WebRequest):
        """Get event dispatcher from DI container"""
        try:
            from ...infrastructure.dependency_injection.container import get_current_container
            container = get_current_container()
            if container:
                return container.get("EventDispatcher")
        except:
            pass
        return None
    
    def _get_persistence_manager(self, request: WebRequest):
        """Get persistence manager from DI container"""
        try:
            from ...infrastructure.dependency_injection.container import get_current_container
            container = get_current_container()
            if container:
                return container.get("PersistenceManager")
        except:
            pass
        return None

class EntityRouteGenerator:
    """
    Generates web routes for StarModel entities.
    
    Automatically creates routes for entity events and CRUD operations
    based on entity definitions and @event decorators.
    """
    
    def __init__(self, registry: RouteRegistry, config: Optional[EntityRouteConfig] = None):
        self.registry = registry
        self.config = config or EntityRouteConfig()
        self.generated_routes: Dict[str, List[Route]] = {}
    
    def generate_entity_routes(self, entity_class: Type['Entity']) -> List[Route]:
        """Generate all routes for an entity class"""
        routes = []
        
        if self.config.enable_events:
            routes.extend(self._generate_event_routes(entity_class))
        
        if self.config.enable_crud:
            routes.extend(self._generate_crud_routes(entity_class))
        
        # Store generated routes
        class_name = entity_class.__name__
        self.generated_routes[class_name] = routes
        
        # Auto-register if enabled
        if self.config.auto_register:
            for route in routes:
                self.registry.register(route)
        
        return routes
    
    def _generate_event_routes(self, entity_class: Type['Entity']) -> List[Route]:
        """Generate routes for entity events"""
        routes = []
        
        # Check if entity has event capabilities
        if not issubclass(entity_class, EventCapable):
            return routes
        
        # Get event methods from entity
        event_methods = entity_class.get_event_methods()
        
        for event_name, event_info in event_methods.items():
            # Determine event type based on method signature
            event_type = self._determine_event_type(event_info)
            
            # Create route handler
            handler = EventRouteHandler(entity_class, event_name, event_type)
            
            # Generate route path
            if event_type == EventRouteType.INSTANCE_EVENT:
                path = f"{self.config.base_path}/{entity_class.__name__.lower()}/{{id}}/events/{event_name}"
            else:
                path = f"{self.config.base_path}/{entity_class.__name__.lower()}/events/{event_name}"
            
            # Determine HTTP method from event metadata
            http_method = self._get_http_method_from_event(event_info)
            
            # Create route
            route = Route(
                path=path,
                method=RouteMethod(http_method.value),
                handler=handler,
                name=f"{entity_class.__name__}.{event_name}",
                metadata={
                    "entity_class": entity_class,
                    "event_name": event_name,
                    "event_type": event_type,
                    "generated": True
                }
            )
            
            routes.append(route)
        
        return routes
    
    def _generate_crud_routes(self, entity_class: Type['Entity']) -> List[Route]:
        """Generate CRUD routes for entity"""
        routes = []
        builder = EntityRouteBuilder(self.registry, entity_class)
        
        # Override base path if configured
        if self.config.base_path != "/entities":
            builder.base_path = f"{self.config.base_path}/{entity_class.__name__.lower()}"
        
        # Import CRUD handlers
        from .crud_routes import CRUDHandler
        crud_handler = CRUDHandler(entity_class)
        
        # Generate standard CRUD routes
        if self.config.enable_list:
            routes.append(builder.list_route(crud_handler))
        
        if self.config.enable_detail:
            routes.append(builder.detail_route(crud_handler))
        
        if self.config.enable_create:
            routes.append(builder.create_route(crud_handler))
        
        if self.config.enable_update:
            routes.append(builder.update_route(crud_handler))
        
        if self.config.enable_delete:
            routes.append(builder.delete_route(crud_handler))
        
        return routes
    
    def _determine_event_type(self, event_info) -> EventRouteType:
        """Determine event type from method signature"""
        # Check if method requires an entity instance
        sig = inspect.signature(event_info.method)
        
        # If first parameter is 'self', it's an instance method
        params = list(sig.parameters.values())
        if params and params[0].name == 'self':
            return EventRouteType.INSTANCE_EVENT
        else:
            return EventRouteType.CLASS_EVENT
    
    def _get_http_method_from_event(self, event_info) -> HttpMethod:
        """Get HTTP method from event metadata"""
        if hasattr(event_info, 'metadata') and event_info.metadata:
            method = event_info.metadata.get('method', 'POST')
            try:
                return HttpMethod(method.upper())
            except ValueError:
                pass
        
        return HttpMethod.POST  # Default to POST
    
    def get_entity_routes(self, entity_class: Type['Entity']) -> List[Route]:
        """Get generated routes for an entity class"""
        class_name = entity_class.__name__
        return self.generated_routes.get(class_name, [])
    
    def regenerate_entity_routes(self, entity_class: Type['Entity']) -> List[Route]:
        """Regenerate routes for an entity class"""
        # Remove existing routes
        class_name = entity_class.__name__
        if class_name in self.generated_routes:
            for route in self.generated_routes[class_name]:
                if route in self.registry.routes:
                    self.registry.routes.remove(route)
                if route.name in self.registry.route_map:
                    del self.registry.route_map[route.name]
        
        # Generate new routes
        return self.generate_entity_routes(entity_class)
    
    def generate_batch_routes(self, entity_classes: List[Type['Entity']]) -> Dict[str, List[Route]]:
        """Generate routes for multiple entity classes"""
        all_routes = {}
        
        for entity_class in entity_classes:
            routes = self.generate_entity_routes(entity_class)
            all_routes[entity_class.__name__] = routes
        
        return all_routes

# Helper functions for route URL generation
def generate_entity_event_url(entity_class: Type['Entity'], event_name: str, 
                             entity_id: Optional[str] = None, **params) -> str:
    """Generate URL for entity event"""
    base_path = f"/entities/{entity_class.__name__.lower()}"
    
    if entity_id:
        url = f"{base_path}/{entity_id}/events/{event_name}"
    else:
        url = f"{base_path}/events/{event_name}"
    
    if params:
        param_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{param_string}"
    
    return url

def generate_entity_crud_url(entity_class: Type['Entity'], operation: str = "list", 
                           entity_id: Optional[str] = None) -> str:
    """Generate URL for entity CRUD operation"""
    base_path = f"/entities/{entity_class.__name__.lower()}"
    
    if operation == "list" or operation == "create":
        return base_path
    elif operation in ["detail", "update", "delete"] and entity_id:
        return f"{base_path}/{entity_id}"
    else:
        return base_path

# Export main components
__all__ = [
    "EntityRouteGenerator", "EventRouteHandler", "EntityRouteConfig",
    "EventRouteType", "generate_entity_event_url", "generate_entity_crud_url"
]