"""
CRUD Route Generator - Standard CRUD Operations

📝 Clean CRUD Web Integration:
This module provides standard CRUD (Create, Read, Update, Delete) route
handlers for StarModel entities, implementing common patterns while
maintaining clean architecture separation.
"""

from typing import Dict, List, Optional, Type, Any
import json
from dataclasses import dataclass

from ..interfaces import WebRequest, WebResponse, RouteHandler, HttpMethod, ResponseBuilder
from ...persistence.repositories import QueryOptions, QueryFilter, QueryOperator

# Forward reference to Entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...entities.lifecycle.entity import Entity

@dataclass
class CRUDConfig:
    """Configuration for CRUD operations"""
    enable_pagination: bool = True
    default_page_size: int = 20
    max_page_size: int = 100
    enable_filtering: bool = True
    enable_sorting: bool = True
    enable_search: bool = True
    search_fields: List[str] = None
    require_authentication: bool = False
    enable_soft_delete: bool = False

class CRUDHandler(RouteHandler):
    """
    Generic CRUD route handler for entities.
    
    Provides standard Create, Read, Update, Delete operations
    for any StarModel entity with clean architecture separation.
    """
    
    def __init__(self, entity_class: Type['Entity'], config: Optional[CRUDConfig] = None):
        self.entity_class = entity_class
        self.config = config or CRUDConfig()
    
    async def handle(self, request: WebRequest) -> WebResponse:
        """Handle CRUD request based on HTTP method and path"""
        method = request.method
        path = request.path
        
        # Determine operation based on method and path
        if method == HttpMethod.GET:
            if self._is_detail_request(request):
                return await self.handle_detail(request)
            else:
                return await self.handle_list(request)
        elif method == HttpMethod.POST:
            return await self.handle_create(request)
        elif method == HttpMethod.PUT:
            return await self.handle_update(request)
        elif method == HttpMethod.DELETE:
            return await self.handle_delete(request)
        else:
            return self._create_error_response("Method not allowed", 405)
    
    def _is_detail_request(self, request: WebRequest) -> bool:
        """Check if request is for a specific entity (has ID)"""
        return request.get_entity_id(self.entity_class) is not None
    
    async def handle_list(self, request: WebRequest) -> WebResponse:
        """Handle entity list request (GET /entities/EntityName)"""
        try:
            # Get repository
            repository = await self._get_repository(request)
            if not repository:
                return self._create_error_response("Repository not available", 500)
            
            # Build query options from request
            query_options = await self._build_query_options(request)
            
            # Execute query
            result = await repository.query(self.entity_class, query_options)
            
            # Convert to response format
            response_data = {
                "entities": [entity.model_dump() if hasattr(entity, 'model_dump') else vars(entity) 
                           for entity in result.entities],
                "total_count": result.total_count,
                "has_more": result.has_more,
                "query_time_ms": result.query_time_ms
            }
            
            return self._create_json_response(response_data)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in list handler for {self.entity_class.__name__}: {e}")
            return self._create_error_response("Internal server error", 500)
    
    async def handle_detail(self, request: WebRequest) -> WebResponse:
        """Handle entity detail request (GET /entities/EntityName/{id})"""
        try:
            # Get entity ID
            entity_id = request.get_entity_id(self.entity_class)
            if not entity_id:
                return self._create_error_response("Entity ID required", 400)
            
            # Get repository
            repository = await self._get_repository(request)
            if not repository:
                return self._create_error_response("Repository not available", 500)
            
            # Load entity
            entity = await repository.load(self.entity_class, entity_id)
            if not entity:
                return self._create_error_response("Entity not found", 404)
            
            # Convert to response format
            response_data = entity.model_dump() if hasattr(entity, 'model_dump') else vars(entity)
            
            return self._create_json_response(response_data)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in detail handler for {self.entity_class.__name__}: {e}")
            return self._create_error_response("Internal server error", 500)
    
    async def handle_create(self, request: WebRequest) -> WebResponse:
        """Handle entity creation request (POST /entities/EntityName)"""
        try:
            # Extract entity data from request
            entity_data = await self._extract_entity_data(request)
            
            # Create entity instance
            entity = self.entity_class(**entity_data)
            
            # Get repository
            repository = await self._get_repository(request)
            if not repository:
                return self._create_error_response("Repository not available", 500)
            
            # Save entity
            entity_id = await repository.save(entity)
            
            # Load saved entity to return
            saved_entity = await repository.load(self.entity_class, entity_id)
            
            # Convert to response format
            response_data = saved_entity.model_dump() if hasattr(saved_entity, 'model_dump') else vars(saved_entity)
            
            return self._create_json_response(response_data, 201)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in create handler for {self.entity_class.__name__}: {e}")
            return self._create_error_response(f"Creation failed: {str(e)}", 400)
    
    async def handle_update(self, request: WebRequest) -> WebResponse:
        """Handle entity update request (PUT /entities/EntityName/{id})"""
        try:
            # Get entity ID
            entity_id = request.get_entity_id(self.entity_class)
            if not entity_id:
                return self._create_error_response("Entity ID required", 400)
            
            # Get repository
            repository = await self._get_repository(request)
            if not repository:
                return self._create_error_response("Repository not available", 500)
            
            # Load existing entity
            entity = await repository.load(self.entity_class, entity_id)
            if not entity:
                return self._create_error_response("Entity not found", 404)
            
            # Extract update data from request
            update_data = await self._extract_entity_data(request)
            
            # Update entity fields
            for field, value in update_data.items():
                if hasattr(entity, field):
                    setattr(entity, field, value)
            
            # Save updated entity
            await repository.save(entity)
            
            # Convert to response format
            response_data = entity.model_dump() if hasattr(entity, 'model_dump') else vars(entity)
            
            return self._create_json_response(response_data)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in update handler for {self.entity_class.__name__}: {e}")
            return self._create_error_response(f"Update failed: {str(e)}", 400)
    
    async def handle_delete(self, request: WebRequest) -> WebResponse:
        """Handle entity deletion request (DELETE /entities/EntityName/{id})"""
        try:
            # Get entity ID
            entity_id = request.get_entity_id(self.entity_class)
            if not entity_id:
                return self._create_error_response("Entity ID required", 400)
            
            # Get repository
            repository = await self._get_repository(request)
            if not repository:
                return self._create_error_response("Repository not available", 500)
            
            # Delete entity
            deleted = await repository.delete(self.entity_class, entity_id)
            
            if deleted:
                return self._create_json_response({"success": True, "message": "Entity deleted"})
            else:
                return self._create_error_response("Entity not found", 404)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in delete handler for {self.entity_class.__name__}: {e}")
            return self._create_error_response(f"Deletion failed: {str(e)}", 400)
    
    async def _build_query_options(self, request: WebRequest) -> QueryOptions:
        """Build query options from request parameters"""
        options = QueryOptions()
        query_params = request.query_params
        
        # Pagination
        if self.config.enable_pagination:
            page = int(query_params.get('page', 1))
            page_size = min(int(query_params.get('page_size', self.config.default_page_size)), 
                          self.config.max_page_size)
            
            options.offset = (page - 1) * page_size
            options.limit = page_size
            options.include_count = True
        
        # Filtering
        if self.config.enable_filtering:
            for key, value in query_params.items():
                if key.startswith('filter_') and len(key) > 7:
                    field_name = key[7:]  # Remove 'filter_' prefix
                    
                    # Parse filter operator (e.g., filter_name__contains=value)
                    if '__' in field_name:
                        field_name, operator = field_name.split('__', 1)
                        query_operator = self._parse_filter_operator(operator)
                    else:
                        query_operator = QueryOperator.EQUALS
                    
                    options.add_filter(field_name, query_operator, value)
        
        # Sorting
        if self.config.enable_sorting:
            sort_by = query_params.get('sort_by')
            if sort_by:
                if sort_by.startswith('-'):
                    # Descending order
                    field_name = sort_by[1:]
                    from ...persistence.repositories.interface import SortDirection
                    options.add_sort(field_name, SortDirection.DESC)
                else:
                    # Ascending order
                    from ...persistence.repositories.interface import SortDirection
                    options.add_sort(sort_by, SortDirection.ASC)
        
        # Search
        if self.config.enable_search:
            search_query = query_params.get('search')
            if search_query and self.config.search_fields:
                # Add contains filter for each search field
                for field in self.config.search_fields:
                    options.add_filter(field, QueryOperator.CONTAINS, search_query)
        
        return options
    
    def _parse_filter_operator(self, operator: str) -> QueryOperator:
        """Parse filter operator from string"""
        operator_map = {
            'eq': QueryOperator.EQUALS,
            'ne': QueryOperator.NOT_EQUALS,
            'gt': QueryOperator.GREATER_THAN,
            'gte': QueryOperator.GREATER_THAN_OR_EQUAL,
            'lt': QueryOperator.LESS_THAN,
            'lte': QueryOperator.LESS_THAN_OR_EQUAL,
            'in': QueryOperator.IN,
            'not_in': QueryOperator.NOT_IN,
            'contains': QueryOperator.CONTAINS,
            'starts_with': QueryOperator.STARTS_WITH,
            'ends_with': QueryOperator.ENDS_WITH,
            'is_null': QueryOperator.IS_NULL,
            'is_not_null': QueryOperator.IS_NOT_NULL
        }
        
        return operator_map.get(operator, QueryOperator.EQUALS)
    
    async def _extract_entity_data(self, request: WebRequest) -> Dict[str, Any]:
        """Extract entity data from request"""
        data = {}
        
        # Try JSON first
        if request.content_type and 'json' in request.content_type:
            try:
                data = await request.json()
            except:
                pass
        
        # Try form data
        if not data and request.method == HttpMethod.POST:
            try:
                form_data = await request.form()
                data = dict(form_data)
            except:
                pass
        
        # Get Datastar payload
        datastar_payload = request.get_datastar_payload()
        data.update(datastar_payload)
        
        return data
    
    async def _get_repository(self, request: WebRequest):
        """Get repository for entity class"""
        try:
            from ...infrastructure.dependency_injection.container import get_current_container
            container = get_current_container()
            if container:
                persistence_manager = container.get("PersistenceManager")
                if persistence_manager:
                    return await persistence_manager.get_repository(self.entity_class)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not get repository: {e}")
        
        return None
    
    def _create_json_response(self, data: Dict[str, Any], status_code: int = 200) -> WebResponse:
        """Create JSON response"""
        from ..adapters.fasthtml import FastHTMLResponse
        response = FastHTMLResponse()
        response.status_code = status_code
        response.set_json(data)
        return response
    
    def _create_error_response(self, message: str, status_code: int) -> WebResponse:
        """Create error response"""
        return self._create_json_response({"error": message}, status_code)

class CRUDRouteGenerator:
    """
    Generator for standard CRUD routes.
    
    Creates standard Create, Read, Update, Delete routes for entities
    with configurable behavior and clean architecture separation.
    """
    
    def __init__(self, config: Optional[CRUDConfig] = None):
        self.config = config or CRUDConfig()
    
    def generate_crud_routes(self, entity_class: Type['Entity'], 
                           base_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate CRUD routes for an entity class"""
        if not base_path:
            base_path = f"/entities/{entity_class.__name__.lower()}"
        
        handler = CRUDHandler(entity_class, self.config)
        
        routes = [
            # List entities
            {
                "path": base_path,
                "method": HttpMethod.GET,
                "handler": handler,
                "name": f"{entity_class.__name__}.list",
                "operation": "list"
            },
            # Get entity detail
            {
                "path": f"{base_path}/{{id}}",
                "method": HttpMethod.GET,
                "handler": handler,
                "name": f"{entity_class.__name__}.detail",
                "operation": "detail"
            },
            # Create entity
            {
                "path": base_path,
                "method": HttpMethod.POST,
                "handler": handler,
                "name": f"{entity_class.__name__}.create",
                "operation": "create"
            },
            # Update entity
            {
                "path": f"{base_path}/{{id}}",
                "method": HttpMethod.PUT,
                "handler": handler,
                "name": f"{entity_class.__name__}.update",
                "operation": "update"
            },
            # Delete entity
            {
                "path": f"{base_path}/{{id}}",
                "method": HttpMethod.DELETE,
                "handler": handler,
                "name": f"{entity_class.__name__}.delete",
                "operation": "delete"
            }
        ]
        
        return routes

# Export main components
__all__ = [
    "CRUDHandler", "CRUDRouteGenerator", "CRUDConfig"
]