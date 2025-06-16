"""
Command Dispatcher

Core command execution system that replaces direct @event route handling.
Implements the APPLICATION SERVICE LAYER pattern from clean architecture.
"""

import inspect
import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from fasthtml.common import Request
from fasthtml.core import _find_p, parse_form, _fix_anno


async def is_datastar_request(request: Request):
    """Check if the request is a Datastar request."""
    if 'datastar' in request.query_params or 'datastar' in request.headers:
        return True
    else:
        content_type = request.headers.get('content-type', '')
            
        if 'application/json' in content_type:
            # Try getting from JSON body (pure JSON requests)
            try:
                datastar_payload = await request.json()
                if datastar_payload:
                    return True
            except Exception:
                return False
        elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
            # Try getting from form data (form submissions)
            try:
                form_data = await parse_form(request)
                if form_data.get('datastar'):
                    return True
            except Exception:
                return False
        else:
            return False
    return False

async def _extract_datastar_payload(request: Request):
    """Extract Datastar payload from request (query params, form data, and JSON body)."""
    from ..core.events import DatastarPayload
    
    datastar_payload = None
    
    try:
        # Try getting datastar from query params first (GET requests)
        datastar_json_str = request.query_params.get('datastar')
        if datastar_json_str:
            datastar_payload = json.loads(datastar_json_str)
        else:
            # For POST requests, try different body formats
            content_type = request.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                # Try getting from JSON body (pure JSON requests)
                try:
                    datastar_payload = await request.json()
                except Exception:
                    pass
            elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
                # Try getting from form data (form submissions)
                try:
                    form_data = await parse_form(request)
                    if hasattr(form_data, 'get'):
                        datastar_json_str = form_data.get('datastar')
                        if datastar_json_str:
                            datastar_payload = json.loads(datastar_json_str)
                except Exception:
                    pass
            else:
                # Fallback: try both JSON and form data
                try:
                    datastar_payload = await request.json()
                except Exception:
                    try:
                        form_data = await parse_form(request)
                        if hasattr(form_data, 'get'):
                            datastar_json_str = form_data.get('datastar')
                            if datastar_json_str:
                                datastar_payload = json.loads(datastar_json_str)
                    except Exception:
                        pass
    except Exception:
        datastar_payload = None
    
    return DatastarPayload(datastar_payload)


async def _find_p_with_datastar(req: Request, arg: str, p, datastar_payload):
    """Extended version of FastHTML's _find_p that also supports Datastar parameters."""
    from ..core.events import DatastarPayload
    
    anno = p.annotation
    
    # Handle special FastHTML parameters first
    if arg.lower() == 'request' or arg.lower() == 'req':
        return req
    if arg.lower() == 'datastar' and (anno is DatastarPayload or anno == DatastarPayload):
        return datastar_payload
    
    # Check query params FIRST, before anything else (highest priority)
    if arg in req.query_params and arg != 'datastar':  # Skip the datastar payload itself
        value = req.query_params[arg]
        # Apply type conversion if needed
        if anno != inspect.Parameter.empty:
            try:
                return _fix_anno(anno, value)
            except Exception:
                # Basic type conversion fallback
                if anno == int:
                    return int(value)
                elif anno == float:
                    return float(value)
                elif anno == bool:
                    return value.lower() in ('true', '1', 'yes')
                return value
        return value
    
    # Try FastHTML's _find_p for other parameters (form data, path params, etc.)
    result = None
    if hasattr(req, 'path_params') and hasattr(req, 'scope'):
        try:
            result = await _find_p(req, arg, p)
        except Exception:
            result = None
    
    # For POST requests, also check form data manually
    if result is None and hasattr(req, 'method') and req.method == 'POST':
        try:
            form_data = await parse_form(req)
            if hasattr(form_data, 'get') and form_data.get(arg) is not None:
                value = form_data.get(arg)
                # Apply type conversion if needed
                if anno != inspect.Parameter.empty:
                    try:
                        return _fix_anno(anno, value)
                    except Exception:
                        # Basic type conversion fallback
                        if anno == int:
                            return int(value)
                        elif anno == float:
                            return float(value)
                        elif anno == bool:
                            return value.lower() in ('true', '1', 'yes')
                        return value
                return value
        except Exception:
            pass
    
    # ONLY if no query param, no form data, and no _find_p result, check datastar payload (lowest priority)
    if result is None:
        # Check datastar payload as fallback
        if datastar_payload and arg in datastar_payload:
            value = datastar_payload[arg]
            # Apply type conversion if needed
            if anno != inspect.Parameter.empty:
                try:
                    return _fix_anno(anno, value)
                except Exception:
                    return value
            return value
    
    return result


async def _wrap_req_with_datastar(req: Request, params: Dict[str, inspect.Parameter], namespace: str = None):
    """Extended version of _wrap_req that supports Datastar parameters."""
    # Extract Datastar payload first
    datastar_payload = await _extract_datastar_payload(req)
    if namespace and namespace in datastar_payload.raw_data:
        # Merge namespaced data into the top level while keeping the original structure
        namespaced_data = datastar_payload.get(namespace, {})
        merged_data = {**datastar_payload.raw_data, **namespaced_data}
        from ..core.events import DatastarPayload
        datastar_payload = DatastarPayload(merged_data)
    
    # Process all parameters with Datastar support
    result = []
    for arg, p in params.items():
        param_value = await _find_p_with_datastar(req, arg, p, datastar_payload)
        result.append(param_value)
    
    return result


async def call_event(entity_class, event_name: str, request: Request) -> Tuple[Any, Dict]:
    """
    Core command execution - replaces direct @event route handling.
    
    This function implements the command dispatcher pattern, separating
    command execution from HTTP routing for clean architecture.
    
    Args:
        entity_class: The entity class containing the event method
        event_name: Name of the event method to execute
        request: FastHTML request object
        
    Returns:
        Tuple of (new_entity_state, command_record)
    """
    # Get event metadata stored by @event decorator
    event_method = getattr(entity_class, event_name)
    
    # If it's an EventMethodDescriptor, get the original method and event info
    if hasattr(event_method, 'original_method'):
        original_method = event_method.original_method
        event_info = event_method._event_info
    else:
        original_method = event_method
        if not hasattr(event_method, '_event_info'):
            raise ValueError(f"Method {event_name} is not decorated with @event")
        event_info = event_method._event_info
    
    # Get current entity state
    entity = entity_class.get(request)
    
    # Use enhanced parameter resolution system with Datastar support
    # This handles all parameter extraction including Datastar payload, form data, and FastHTML special params
    namespace = getattr(entity, 'namespace', None) if hasattr(entity, 'use_namespace') and entity.use_namespace else None
    wrapped_params = await _wrap_req_with_datastar(request, event_info.signature.parameters, namespace=namespace)
    
    # Call the method with resolved parameters (skip 'self' which is index 0)
    # The entity instance replaces 'self', so we use entity + params[1:]
    method_params = [entity] + wrapped_params[1:]
    
    # Execute the command using the original method with resolved parameters
    if inspect.iscoroutinefunction(original_method):
        result = await original_method(*method_params)
    else:
        result = original_method(*method_params)
    
    # If the method returned a new entity state, use it; otherwise use the original
    if hasattr(result, '__dict__') and hasattr(result, 'id'):
        new_entity = result
    else:
        new_entity = entity
    
    # Create synthetic command record for event bus and debugging
    # Build args dict from method signature and resolved parameters
    args_dict = {}
    param_names = list(event_info.signature.parameters.keys())
    for i, param_value in enumerate(method_params):
        if i < len(param_names):
            args_dict[param_names[i]] = param_value
    
    command_record = {
        "entity": f"{entity_class.__name__}:{entity.id}",
        "event": event_name,
        "args": args_dict,
        "actor": None,  # Simplified for now
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "event_info": event_info,  # Include event info for response handling
    }
    
    return new_entity, command_record