"""
FastHTML Web Adapter

Provides a simple configure_app function to set up FastHTML with StarModel.
Uses FastHTMLDispatcher internally for FastHTML-specific optimizations.
"""

import inspect
from typing import Type, Callable, List
from starlette.requests import Request

from ..app.dispatcher import Dispatcher, setup_datastar_middleware
from ..app.uow import UnitOfWork
from ..core.entity import Entity
from ..core.events import EventInfo
from ..core import singleton

@singleton
class FastHTMLDispatcher(Dispatcher):
    """FastHTML-specific dispatcher that only overrides what's needed."""
    
    def _register_route(self, router, path: str, handler: Callable, event_info: EventInfo):
        """Register route using FastHTML's decorator pattern."""
        method = event_info.method if hasattr(event_info, 'method') else 'GET'
        router(path, methods=[method])(handler)
    
    def _create_route_handler(
        self,
        entity_class: Type[Entity], 
        event_name: str, 
        event_info: EventInfo
    ) -> Callable:
        """Create FastHTML-specific route handler with proper signature."""
        # Get base handler from parent
        base_handler = super()._create_route_handler(entity_class, event_name, event_info)
        
        # Construct FastHTML-compatible signature
        sig = event_info.signature
        params = list(sig.parameters.values())
        if params and params[0].name == "self": 
            params.pop(0)

        # TODO do not use string to check this Add request parameter if not present
        if "request" not in [p.name for p in params]:
            new_param = inspect.Parameter(
                "request",
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=Request
            )
            params.append(new_param)

        base_handler.__signature__ = sig.replace(parameters=params)
        return base_handler


def configure_app(app, rt, entity_classes: List[Type[Entity]] = None):
    """
    Configure FastHTML app with StarModel entities.
    
    This is the main entry point for FastHTML integration. Simply import and call:
    
    ```python
    from starmodel.adapters.fasthtml import configure_app
    app, rt = fast_app()
    configure_app(app, rt)
    ```
    
    Args:
        app: FastHTML app instance
        rt: FastHTML router instance  
        entity_classes: Optional list of specific entities to register.
                       If None, registers all Entity subclasses.
                       
    Returns:
        The configured app instance
    """
    # Create FastHTML-specific dispatcher
    dispatcher = FastHTMLDispatcher()
    
    # Set up middleware for datastar parameter extraction
    setup_datastar_middleware(app, dispatcher)
    
    # Register entities using the clean dispatcher interface
    dispatcher.include_entities(rt, entity_classes)
    
    return app


# Legacy functions for backward compatibility
def register_all_entities(router):
    """Legacy function - use configure_app instead."""
    try:
        dispatcher = FastHTMLDispatcher()
        dispatcher.include_entities(router)
    except Exception as e:
        print(f"Error registering all entities: {e}")


def register_entities(router, uow: UnitOfWork, entity_classes: list = []):
    """Legacy function - use configure_app instead."""     
    dispatcher = FastHTMLDispatcher(uow)
    dispatcher.include_entities(router, entity_classes or None)