"""
FastAPI Web Adapter

Provides a simple configure_app function to set up FastAPI with StarModel.
Uses FastAPIDispatcher internally for FastAPI-specific optimizations.
"""

import inspect
from typing import Type, Callable, List
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.requests import Request

from ..app.dispatcher import Dispatcher
from ..app.datastar import explode_datastar_params_in_request, is_datastar_request
from ..app.uow import UnitOfWork
from ..core.entity import Entity
from ..core.events import EventInfo
from ..ui import TagResponse


class UnpackDatastar(APIRoute):
    """FastAPI route class that handles datastar parameter extraction."""
    
    def get_route_handler(self):
        original = super().get_route_handler()

        async def custom_route(request: Request):
            if await is_datastar_request(request):
                event_method = self.dependant.call
                namespace = event_method._entity_class._namespace
                await explode_datastar_params_in_request(request, namespace)

            return await original(request)

        return custom_route

class FastAPIDispatcher(Dispatcher):
    """FastAPI-specific dispatcher that only overrides what's needed."""
    
    def _register_route(self, router, path: str, handler: Callable, event_info: EventInfo):
        """Register route using FastAPI's add_api_route method."""
        method = event_info.method if hasattr(event_info, 'method') else 'GET'
        router.add_api_route(path, handler, methods=[method])
    
    def _create_route_handler(
        self,
        entity_class: Type[Entity], 
        event_name: str, 
        event_info: EventInfo
    ) -> Callable:
        """Create FastAPI-specific route handler with proper signature."""
        # Get base handler from parent
        base_handler = super()._create_route_handler(entity_class, event_name, event_info)
        
        # Construct FastAPI-compatible signature
        sig = event_info.signature
        params = list(sig.parameters.values())
        if params and params[0].name == "self": 
            params.pop(0) 

        # Add request parameter if not present
        if not any(p.annotation == Request for p in params):
            new_param = inspect.Parameter(
                "request",
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=Request
            )
            params.append(new_param)

        base_handler.__signature__ = sig.replace(parameters=params)
        return base_handler
    
    async def command_to_response(self, command_record, entity, request):
        """Override to provide FastAPI-specific error handling."""
        try:
            return await super().command_to_response(command_record, entity, request)
        except Exception as e:
            # Return JSON error response for FastAPI
            return {"error": f"Error in {command_record.get('event', 'unknown')}: {str(e)}"}


def configure_app(app, entity_classes: List[Type[Entity]] = None, base_path: str = ""):
    """
    Configure FastAPI app with StarModel entities.
    
    This is the main entry point for FastAPI integration. Simply import and call:
    
    ```python
    from starmodel.adapters.fastapi import configure_app
    app = FastAPI()
    configure_app(app)
    ```
    
    Args:
        app: FastAPI app instance
        entity_classes: Optional list of specific entities to register.
                       If None, registers all Entity subclasses.
        base_path: Optional base path for all routes (e.g., "/api/v1")
                       
    Returns:
        The configured app instance
    """
    # Create FastAPI-specific dispatcher
    dispatcher = FastAPIDispatcher()
    
    # Create router with UnpackDatastar route class for datastar support
    router = APIRouter(route_class=UnpackDatastar, default_response_class=TagResponse)
    
    # Register entities using the clean dispatcher interface
    dispatcher.include_entities(router, entity_classes, base_path)
    
    # Include router in app
    app.include_router(router)
    app.router.default_response_class = TagResponse

    return app


# Legacy functions for backward compatibility
def register_all_entities(router):
    """Legacy function - use configure_app instead."""
    try:
        dispatcher = FastAPIDispatcher()
        dispatcher.include_entities(router)
    except Exception as e:
        print(f"Error registering all entities: {e}")


def register_entities(router, entity_classes: list, uow: UnitOfWork):
    """Legacy function - use configure_app instead."""
    dispatcher = FastAPIDispatcher(uow)
    dispatcher.include_entities(router, entity_classes)