"""
Web Routing - Framework-Agnostic Route Management

🛣️ Clean Route Architecture:
This module provides route management and registration capabilities
that work across different web frameworks while maintaining clean
separation between routing logic and domain logic.
"""

from typing import Dict, List, Optional, Callable, Any, Pattern
from dataclasses import dataclass, field
from enum import Enum
import re
from abc import ABC, abstractmethod

from .interfaces import HttpMethod, RouteHandler, WebRequest, WebResponse

class RouteMethod(Enum):
    """Route methods (alias for HttpMethod for routing context)"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    ANY = "*"  # Matches any method

@dataclass
class RouteParameter:
    """Route parameter definition"""
    name: str
    type: type = str
    required: bool = True
    default: Any = None
    pattern: Optional[str] = None

@dataclass
class Route:
    """Route definition"""
    path: str
    method: RouteMethod
    handler: RouteHandler
    name: Optional[str] = None
    parameters: List[RouteParameter] = field(default_factory=list)
    middleware: List[Callable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Compiled route pattern
    _pattern: Optional[Pattern] = field(default=None, init=False)
    _param_names: List[str] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """Compile route pattern after initialization"""
        self._compile_pattern()
    
    def _compile_pattern(self):
        """Compile route path into regex pattern"""
        # Convert Flask/FastAPI-style route patterns to regex
        pattern = self.path
        param_names = []
        
        # Handle path parameters like {id} or {id:int}
        import re
        param_pattern = r'\{([^:}]+)(?::([^}]+))?\}'
        
        def replace_param(match):
            param_name = match.group(1)
            param_type = match.group(2) or 'str'
            param_names.append(param_name)
            
            # Add parameter info if not already present
            if not any(p.name == param_name for p in self.parameters):
                param_type_class = str
                if param_type == 'int':
                    param_type_class = int
                elif param_type == 'float':
                    param_type_class = float
                
                self.parameters.append(RouteParameter(
                    name=param_name,
                    type=param_type_class
                ))
            
            # Return regex pattern for parameter
            if param_type == 'int':
                return r'(\d+)'
            elif param_type == 'float':
                return r'(\d+\.\d+|\d+)'
            else:
                return r'([^/]+)'
        
        pattern = re.sub(param_pattern, replace_param, pattern)
        
        # Ensure pattern matches exactly
        pattern = f"^{pattern}$"
        
        self._pattern = re.compile(pattern)
        self._param_names = param_names
    
    def matches(self, path: str) -> Optional[Dict[str, Any]]:
        """Check if route matches path and extract parameters"""
        if not self._pattern:
            return None
        
        match = self._pattern.match(path)
        if not match:
            return None
        
        # Extract parameters
        params = {}
        for i, param_name in enumerate(self._param_names):
            if i < len(match.groups()):
                param_value = match.group(i + 1)
                
                # Convert to appropriate type
                param_def = next((p for p in self.parameters if p.name == param_name), None)
                if param_def and param_def.type == int:
                    param_value = int(param_value)
                elif param_def and param_def.type == float:
                    param_value = float(param_value)
                
                params[param_name] = param_value
        
        return params
    
    def generate_url(self, **params) -> str:
        """Generate URL from route template with parameters"""
        url = self.path
        
        # Replace parameters in path
        for param_name, param_value in params.items():
            pattern = f"{{{param_name}}}"
            type_pattern = f"{{{param_name}:int}}"
            float_pattern = f"{{{param_name}:float}}"
            
            url = url.replace(pattern, str(param_value))
            url = url.replace(type_pattern, str(param_value))
            url = url.replace(float_pattern, str(param_value))
        
        return url

class RouteRegistry:
    """
    Central route registry for managing application routes.
    
    Provides framework-agnostic route registration and lookup,
    enabling clean separation between routing and domain logic.
    """
    
    def __init__(self):
        self.routes: List[Route] = []
        self.route_map: Dict[str, Route] = {}  # name -> route
        self.middleware_stack: List[Callable] = []
    
    def register(self, route: Route) -> Route:
        """Register a route"""
        self.routes.append(route)
        
        if route.name:
            self.route_map[route.name] = route
        
        return route
    
    def add_route(self, 
                  path: str,
                  method: RouteMethod,
                  handler: RouteHandler,
                  name: Optional[str] = None,
                  **kwargs) -> Route:
        """Add a route with fluent interface"""
        route = Route(
            path=path,
            method=method,
            handler=handler,
            name=name,
            **kwargs
        )
        return self.register(route)
    
    def get(self, path: str, handler: RouteHandler, name: Optional[str] = None, **kwargs) -> Route:
        """Register GET route"""
        return self.add_route(path, RouteMethod.GET, handler, name, **kwargs)
    
    def post(self, path: str, handler: RouteHandler, name: Optional[str] = None, **kwargs) -> Route:
        """Register POST route"""
        return self.add_route(path, RouteMethod.POST, handler, name, **kwargs)
    
    def put(self, path: str, handler: RouteHandler, name: Optional[str] = None, **kwargs) -> Route:
        """Register PUT route"""
        return self.add_route(path, RouteMethod.PUT, handler, name, **kwargs)
    
    def delete(self, path: str, handler: RouteHandler, name: Optional[str] = None, **kwargs) -> Route:
        """Register DELETE route"""
        return self.add_route(path, RouteMethod.DELETE, handler, name, **kwargs)
    
    def find_route(self, method: str, path: str) -> Optional[tuple[Route, Dict[str, Any]]]:
        """Find matching route for method and path"""
        route_method = RouteMethod(method.upper()) if method.upper() in [m.value for m in RouteMethod] else None
        
        for route in self.routes:
            # Check method match
            if route.method != RouteMethod.ANY and route_method != route.method:
                continue
            
            # Check path match
            params = route.matches(path)
            if params is not None:
                return route, params
        
        return None
    
    def get_route_by_name(self, name: str) -> Optional[Route]:
        """Get route by name"""
        return self.route_map.get(name)
    
    def generate_url(self, name: str, **params) -> Optional[str]:
        """Generate URL for named route"""
        route = self.get_route_by_name(name)
        if route:
            return route.generate_url(**params)
        return None
    
    def add_middleware(self, middleware: Callable):
        """Add global middleware"""
        self.middleware_stack.append(middleware)
    
    def get_routes_for_method(self, method: RouteMethod) -> List[Route]:
        """Get all routes for a specific method"""
        return [route for route in self.routes 
                if route.method == method or route.method == RouteMethod.ANY]
    
    def get_all_routes(self) -> List[Route]:
        """Get all registered routes"""
        return self.routes.copy()
    
    def clear(self):
        """Clear all routes"""
        self.routes.clear()
        self.route_map.clear()

class EntityRouteBuilder:
    """
    Builder for creating entity-specific routes.
    
    Provides a fluent interface for creating routes that handle
    entity operations in a clean, declarative way.
    """
    
    def __init__(self, registry: RouteRegistry, entity_class: type):
        self.registry = registry
        self.entity_class = entity_class
        self.base_path = f"/entities/{entity_class.__name__.lower()}"
    
    def list_route(self, handler: RouteHandler, path: Optional[str] = None) -> Route:
        """Create route for listing entities"""
        route_path = path or self.base_path
        return self.registry.get(route_path, handler, f"{self.entity_class.__name__}.list")
    
    def detail_route(self, handler: RouteHandler, path: Optional[str] = None) -> Route:
        """Create route for entity detail"""
        route_path = path or f"{self.base_path}/{{id}}"
        return self.registry.get(route_path, handler, f"{self.entity_class.__name__}.detail")
    
    def create_route(self, handler: RouteHandler, path: Optional[str] = None) -> Route:
        """Create route for creating entities"""
        route_path = path or self.base_path
        return self.registry.post(route_path, handler, f"{self.entity_class.__name__}.create")
    
    def update_route(self, handler: RouteHandler, path: Optional[str] = None) -> Route:
        """Create route for updating entities"""
        route_path = path or f"{self.base_path}/{{id}}"
        return self.registry.put(route_path, handler, f"{self.entity_class.__name__}.update")
    
    def delete_route(self, handler: RouteHandler, path: Optional[str] = None) -> Route:
        """Create route for deleting entities"""
        route_path = path or f"{self.base_path}/{{id}}"
        return self.registry.delete(route_path, handler, f"{self.entity_class.__name__}.delete")
    
    def event_route(self, event_name: str, handler: RouteHandler, 
                   method: RouteMethod = RouteMethod.POST,
                   path: Optional[str] = None) -> Route:
        """Create route for entity event"""
        route_path = path or f"{self.base_path}/{{id}}/events/{event_name}"
        route_name = f"{self.entity_class.__name__}.{event_name}"
        return self.registry.add_route(route_path, method, handler, route_name)
    
    def class_event_route(self, event_name: str, handler: RouteHandler,
                         method: RouteMethod = RouteMethod.POST,
                         path: Optional[str] = None) -> Route:
        """Create route for class-level entity event"""
        route_path = path or f"{self.base_path}/events/{event_name}"
        route_name = f"{self.entity_class.__name__}.class.{event_name}"
        return self.registry.add_route(route_path, method, handler, route_name)

# Route decorators for clean syntax
class RouteDecorator:
    """Decorator class for route registration"""
    
    def __init__(self, registry: RouteRegistry):
        self.registry = registry
    
    def route(self, path: str, method: RouteMethod = RouteMethod.GET, name: Optional[str] = None):
        """Route decorator"""
        def decorator(handler_func):
            # Convert function to RouteHandler if needed
            if not isinstance(handler_func, RouteHandler):
                handler = FunctionRouteHandler(handler_func)
            else:
                handler = handler_func
            
            self.registry.add_route(path, method, handler, name)
            return handler_func
        
        return decorator
    
    def get(self, path: str, name: Optional[str] = None):
        """GET route decorator"""
        return self.route(path, RouteMethod.GET, name)
    
    def post(self, path: str, name: Optional[str] = None):
        """POST route decorator"""
        return self.route(path, RouteMethod.POST, name)
    
    def put(self, path: str, name: Optional[str] = None):
        """PUT route decorator"""
        return self.route(path, RouteMethod.PUT, name)
    
    def delete(self, path: str, name: Optional[str] = None):
        """DELETE route decorator"""
        return self.route(path, RouteMethod.DELETE, name)

class FunctionRouteHandler(RouteHandler):
    """Route handler that wraps a function"""
    
    def __init__(self, func: Callable):
        self.func = func
    
    async def handle(self, request: WebRequest) -> WebResponse:
        """Handle request using wrapped function"""
        # Call function with request
        if asyncio.iscoroutinefunction(self.func):
            result = await self.func(request)
        else:
            result = self.func(request)
        
        # Convert result to WebResponse if needed
        if isinstance(result, WebResponse):
            return result
        else:
            # Create response from result
            response = request.adapter.create_response() if hasattr(request, 'adapter') else None
            if response:
                response.set_content(result)
                return response
            else:
                # Fallback - this should be handled by the adapter
                raise NotImplementedError("Cannot create response without adapter")

# Export main components
__all__ = [
    "RouteRegistry", "Route", "RouteMethod", "RouteParameter",
    "EntityRouteBuilder", "RouteDecorator", "FunctionRouteHandler"
]