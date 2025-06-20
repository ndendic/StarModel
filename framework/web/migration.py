"""
Web Route Migration - Legacy to Clean Architecture Migration

🔄 Clean Migration Patterns:
This module provides migration helpers and examples for converting
existing web routes to use the new clean architecture web layer,
ensuring smooth transition from legacy patterns.
"""

from typing import List, Type, Dict, Any, Callable, Optional
import inspect
from dataclasses import dataclass

from .interfaces import WebRequest, WebResponse, HttpMethod
from .integration import WebIntegration, web_integration_builder
from .adapters.fasthtml import FastHTMLAdapter, create_fasthtml_adapter

# Forward reference to Entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..entities.lifecycle.entity import Entity

@dataclass
class MigrationExample:
    """Example of how to migrate a specific pattern"""
    title: str
    description: str
    legacy_code: str
    new_code: str
    explanation: str

class WebRouteMigrationGuide:
    """
    Guide for migrating existing web routes to clean architecture.
    
    Provides examples and helpers for common migration patterns,
    showing how to transform legacy route handlers to use the
    new clean architecture web layer.
    """
    
    def __init__(self):
        self.examples = self._create_migration_examples()
    
    def _create_migration_examples(self) -> List[MigrationExample]:
        """Create migration examples for common patterns"""
        return [
            self._entity_event_route_example(),
            self._fasthtml_route_example(),
            self._entity_crud_example(),
            self._middleware_example(),
            self._session_handling_example()
        ]
    
    def _entity_event_route_example(self) -> MigrationExample:
        """Example of migrating entity event routes"""
        return MigrationExample(
            title="Entity Event Routes",
            description="Migrate direct entity method routes to use event dispatcher",
            legacy_code='''
# LEGACY: Direct entity method routing
from fasthtml.common import *
from app.entities.counter import Counter

app = FastHTML()

@app.post("/counter/increment")
def increment_counter(req):
    counter = Counter.get(req)
    counter.increment()
    counter.save()
    return counter.render()
            ''',
            new_code='''
# NEW: Clean architecture with event dispatcher
from framework.web import FastHTMLAdapter, web_integration_builder
from framework.web.adapters.fasthtml import create_fasthtml_adapter
from app.entities.counter import Counter

# Create adapter and integration
adapter = create_fasthtml_adapter()
integration = await (web_integration_builder(adapter)
    .with_entities(Counter)
    .with_base_path("/api")
    .build())

# Routes are automatically generated:
# POST /api/counter/{id}/events/increment
# The event dispatcher handles entity loading, method execution, and persistence
            ''',
            explanation='''
The new approach:
1. Automatically generates routes for @event methods
2. Uses event dispatcher for clean command execution
3. Handles entity loading/saving through repository pattern
4. Separates domain logic from web concerns
5. Provides consistent error handling and validation
            '''
        )
    
    def _fasthtml_route_example(self) -> MigrationExample:
        """Example of migrating FastHTML routes"""
        return MigrationExample(
            title="FastHTML Route Handlers",
            description="Migrate FastHTML route handlers to use web abstraction",
            legacy_code='''
# LEGACY: Direct FastHTML route handlers
from fasthtml.common import *

app = FastHTML()

@app.get("/users/{user_id}")
def get_user(user_id: str, req):
    # Direct database access
    user = get_user_from_db(user_id)
    if not user:
        return "User not found", 404
    
    return Div(
        H1(user.name),
        P(user.email)
    )
            ''',
            new_code='''
# NEW: Clean architecture route handler
from framework.web.interfaces import WebRequest, WebResponse, RouteHandler
from framework.web.adapters.fasthtml import FastHTMLResponse

class UserDetailHandler(RouteHandler):
    async def handle(self, request: WebRequest) -> WebResponse:
        user_id = request.path.split('/')[-1]
        
        # Use repository through DI container
        user_repo = self._get_user_repository(request)
        user = await user_repo.load(User, user_id)
        
        response = FastHTMLResponse()
        if not user:
            response.status_code = 404
            response.set_html("User not found")
        else:
            html = str(Div(H1(user.name), P(user.email)))
            response.set_html(html)
        
        return response

# Register with integration
integration.register_route(HttpMethod.GET, "/users/{user_id}", UserDetailHandler())
            ''',
            explanation='''
Benefits of the new approach:
1. Framework-agnostic route handlers
2. Proper dependency injection for repositories
3. Clean error handling patterns
4. Testable without web framework
5. Consistent response handling
            '''
        )
    
    def _entity_crud_example(self) -> MigrationExample:
        """Example of migrating CRUD operations"""
        return MigrationExample(
            title="CRUD Operations",
            description="Migrate manual CRUD routes to automatic generation",
            legacy_code='''
# LEGACY: Manual CRUD routes
@app.get("/products")
def list_products(req):
    products = Product.all()
    return [p.to_dict() for p in products]

@app.get("/products/{id}")
def get_product(id: str, req):
    product = Product.get(id)
    return product.to_dict() if product else ("Not found", 404)

@app.post("/products")
def create_product(req):
    data = req.json()
    product = Product(**data)
    product.save()
    return product.to_dict()
            ''',
            new_code='''
# NEW: Automatic CRUD generation
from framework.web.generators import CRUDConfig
from app.entities.product import Product

# Configure CRUD behavior
crud_config = CRUDConfig(
    enable_pagination=True,
    enable_filtering=True,
    enable_search=True,
    search_fields=["name", "description"]
)

# CRUD routes are automatically generated:
# GET /entities/product - list with pagination/filtering
# GET /entities/product/{id} - get single product
# POST /entities/product - create new product
# PUT /entities/product/{id} - update product
# DELETE /entities/product/{id} - delete product

integration = await (web_integration_builder(adapter)
    .with_entities(Product)
    .build())
            ''',
            explanation='''
Automatic CRUD provides:
1. Consistent API patterns across entities
2. Built-in pagination, filtering, and search
3. Proper error handling and validation
4. Repository pattern for data access
5. Configurable behavior per entity
            '''
        )
    
    def _middleware_example(self) -> MigrationExample:
        """Example of migrating middleware"""
        return MigrationExample(
            title="Middleware",
            description="Migrate middleware to use clean architecture patterns",
            legacy_code='''
# LEGACY: FastHTML-specific middleware
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Direct request manipulation
        if not request.headers.get("authorization"):
            return Response("Unauthorized", 401)
        
        response = await call_next(request)
        return response

app.add_middleware(AuthMiddleware)
            ''',
            new_code='''
# NEW: Framework-agnostic middleware
from framework.web.interfaces import WebRequest, WebResponse

async def auth_middleware(request: WebRequest, call_next):
    """Framework-agnostic authentication middleware"""
    auth_header = request.headers.get("authorization")
    if not auth_header:
        response = request.adapter.create_response()
        response.status_code = 401
        response.set_text("Unauthorized")
        return response
    
    # Continue processing
    return await call_next(request)

# Register with integration
integration.add_middleware(auth_middleware)
            ''',
            explanation='''
Framework-agnostic middleware:
1. Works with any web framework adapter
2. Uses clean abstractions for requests/responses
3. Easier to test without web framework
4. Consistent across different deployment scenarios
5. Can be shared between projects
            '''
        )
    
    def _session_handling_example(self) -> MigrationExample:
        """Example of migrating session handling"""
        return MigrationExample(
            title="Session Management",
            description="Migrate session handling to use clean architecture session manager",
            legacy_code='''
# LEGACY: Direct session manipulation
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key="secret")

@app.get("/profile")
def get_profile(req):
    user_id = req.session.get("user_id")
    if not user_id:
        return redirect("/login")
    
    user = User.get(user_id)
    return render_profile(user)
            ''',
            new_code='''
# NEW: Clean architecture session management
from framework.web.session import SessionConfig, SessionStorage

# Configure session management
session_config = SessionConfig(
    storage=SessionStorage.MEMORY,
    session_lifetime=timedelta(hours=24),
    cookie_name="starmodel_session"
)

# Create integration with sessions
integration = await (web_integration_builder(adapter)
    .with_sessions(session_config)
    .build())

# Use in route handlers
class ProfileHandler(RouteHandler):
    async def handle(self, request: WebRequest) -> WebResponse:
        session = request.get_session()
        user_id = session.get("user_id")
        
        if not user_id:
            response = request.adapter.create_response()
            response.set_redirect("/login")
            return response
        
        # Use repository to get user
        user_repo = self._get_user_repository(request)
        user = await user_repo.load(User, user_id)
        
        response = request.adapter.create_response()
        response.set_html(render_profile(user))
        return response
            ''',
            explanation='''
Clean session management provides:
1. Framework-agnostic session abstraction
2. Pluggable storage backends
3. Consistent session API across frameworks
4. Built-in security features
5. Easy testing and mocking
            '''
        )
    
    def get_examples(self) -> List[MigrationExample]:
        """Get all migration examples"""
        return self.examples
    
    def get_example_by_title(self, title: str) -> Optional[MigrationExample]:
        """Get specific migration example"""
        for example in self.examples:
            if example.title == title:
                return example
        return None
    
    def print_migration_guide(self):
        """Print complete migration guide"""
        print("# StarModel Web Layer Migration Guide\n")
        print("This guide shows how to migrate existing web routes to use the new clean architecture web layer.\n")
        
        for i, example in enumerate(self.examples, 1):
            print(f"## {i}. {example.title}\n")
            print(f"{example.description}\n")
            print("### Legacy Code:\n")
            print("```python")
            print(example.legacy_code.strip())
            print("```\n")
            print("### New Code:\n")
            print("```python")
            print(example.new_code.strip())
            print("```\n")
            print("### Explanation:\n")
            print(example.explanation.strip())
            print("\n" + "="*80 + "\n")

class LegacyRouteAnalyzer:
    """
    Analyzes legacy route handlers to suggest migration patterns.
    
    Scans existing code to identify patterns that should be migrated
    to the new clean architecture approach.
    """
    
    def __init__(self):
        self.migration_suggestions = []
    
    def analyze_function(self, func: Callable) -> Dict[str, Any]:
        """Analyze a route handler function for migration opportunities"""
        suggestions = {
            "function_name": func.__name__,
            "suggestions": [],
            "complexity": "low"
        }
        
        # Get function source
        try:
            source = inspect.getsource(func)
            suggestions["source"] = source
        except:
            return suggestions
        
        # Check for direct entity access patterns
        if "get(" in source or ".save(" in source:
            suggestions["suggestions"].append({
                "type": "entity_access",
                "message": "Consider using repository pattern instead of direct entity access",
                "priority": "high"
            })
        
        # Check for direct database queries
        if any(keyword in source for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE"]):
            suggestions["suggestions"].append({
                "type": "direct_sql",
                "message": "Move SQL queries to repository layer",
                "priority": "high"
            })
        
        # Check for session access
        if "session" in source and "req.session" in source:
            suggestions["suggestions"].append({
                "type": "session_access",
                "message": "Use clean architecture session management",
                "priority": "medium"
            })
        
        # Check for hard-coded responses
        if "return (" in source and any(code in source for code in ["404", "500", "401"]):
            suggestions["suggestions"].append({
                "type": "response_handling",
                "message": "Use WebResponse abstraction for consistent response handling",
                "priority": "medium"
            })
        
        # Calculate complexity
        if len(suggestions["suggestions"]) > 3:
            suggestions["complexity"] = "high"
        elif len(suggestions["suggestions"]) > 1:
            suggestions["complexity"] = "medium"
        
        return suggestions
    
    def analyze_module(self, module) -> List[Dict[str, Any]]:
        """Analyze all route handlers in a module"""
        results = []
        
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj):
                # Check if it looks like a route handler
                if any(decorator in str(obj) for decorator in ["@app.", "@rt.", "@get", "@post"]):
                    analysis = self.analyze_function(obj)
                    if analysis["suggestions"]:
                        results.append(analysis)
        
        return results

# Convenience functions for common migration patterns
def create_fasthtml_migration_integration(entities: List[Type['Entity']] = None) -> WebIntegration:
    """Create a standard FastHTML integration for migration"""
    import asyncio
    
    async def setup():
        adapter = create_fasthtml_adapter()
        builder = web_integration_builder(adapter)
        
        if entities:
            builder = builder.with_entities(*entities)
        
        return await (builder
            .with_cors()
            .with_sessions()
            .debug_mode(True)
            .build())
    
    return asyncio.run(setup())

def migrate_entity_routes(entity_class: Type['Entity'], integration: WebIntegration):
    """Migrate an entity's routes to use automatic generation"""
    integration.register_entity(entity_class)
    routes = integration.get_entity_routes(entity_class)
    
    print(f"Generated {len(routes)} routes for {entity_class.__name__}:")
    for route in routes:
        print(f"  {route.method.value} {route.path} -> {route.name}")

# Export main components
__all__ = [
    "WebRouteMigrationGuide", "MigrationExample", "LegacyRouteAnalyzer",
    "create_fasthtml_migration_integration", "migrate_entity_routes"
]