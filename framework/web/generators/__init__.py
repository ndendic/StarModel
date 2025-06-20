"""
Web Route Generators - Automatic Route Generation

🛣️ Clean Route Generation:
This module provides automatic route generation for StarModel entities,
extracting web routing concerns from domain logic while maintaining
clean architecture separation.

Components:
- EntityRouteGenerator: Automatic entity routes
- EventRouteGenerator: Event method routes
- CRUDRouteGenerator: Standard CRUD operations
"""

from .entity_routes import EntityRouteGenerator, EventRouteHandler
from .crud_routes import CRUDRouteGenerator, CRUDHandler

__all__ = [
    "EntityRouteGenerator", "EventRouteHandler",
    "CRUDRouteGenerator", "CRUDHandler"
]