"""
FastHTML Dependency Injection Integration

This module extends FastHTML's parameter injection system to automatically inject
FastState state types based on function signatures and type annotations.
"""

import inspect
import asyncio
from functools import wraps
from typing import Any, Callable
from fasthtml.common import Request

from .registry import state_registry
from .auth import set_current_auth, set_user_permissions, set_user_roles, set_user_id, clear_auth_context


def patch_fasthtml_for_state_injection():
    """
    Extend FastHTML's parameter injection system to handle state types.
    
    This function monkey patches FastHTML's core functionality to recognize
    state types and automatically inject them based on the state registry
    configuration.
    
    The patching happens at the route handler level to ensure compatibility
    with FastHTML's existing parameter injection system.
    """
    try:
        # Import FastHTML core modules
        import fasthtml.core
        from fasthtml.core import FastHTML
        
        # Store original add_route method
        original_add_route = FastHTML.add_route
        
        def enhanced_add_route(self, *args, **kwargs):
            """Enhanced route addition that wraps handlers with state injection."""
            
            # Handle different call patterns from FastHTML
            if len(args) >= 2:
                # Called as add_route(path, endpoint, ...)
                path, endpoint = args[0], args[1]
                remaining_args = args[2:]
            elif len(args) == 1 and hasattr(args[0], '__call__'):
                # Called as add_route(route_object)
                return original_add_route(self, *args, **kwargs)
            else:
                # Unknown pattern, pass through
                return original_add_route(self, *args, **kwargs)
            
            # Inspect the endpoint function for state parameters
            if callable(endpoint):
                sig = inspect.signature(endpoint)
                state_params = []
                
                for param_name, param in sig.parameters.items():
                    if state_registry.is_state_type(param.annotation):
                        state_params.append((param_name, param.annotation))
                
                if state_params:
                    # Create wrapper that injects states
                    if asyncio.iscoroutinefunction(endpoint):
                        @wraps(endpoint)
                        async def async_state_injecting_wrapper(*args, **kwargs):
                            try:
                                # Extract special FastHTML parameters
                                req = kwargs.get('req') or kwargs.get('request')
                                sess = kwargs.get('sess') or kwargs.get('session') or {}
                                auth = kwargs.get('auth')
                                
                                if not req:
                                    # Try to find request in args
                                    for arg in args:
                                        if isinstance(arg, Request):
                                            req = arg
                                            break
                                
                                if not req:
                                    raise ValueError("Request object not available for state injection")
                                
                                # Set auth context for the request
                                _setup_auth_context(auth, req, sess)
                                
                                # Inject state instances
                                for param_name, state_type in state_params:
                                    if param_name not in kwargs:
                                        try:
                                            state_instance = state_registry.resolve_state(state_type, req, sess, auth)
                                            kwargs[param_name] = state_instance
                                        except Exception as e:
                                            # Handle auth/permission errors gracefully
                                            if isinstance(e, (PermissionError, ValueError)):
                                                # Return error response
                                                from fasthtml.common import P, Div
                                                return Div(
                                                    P(f"Authentication Error: {str(e)}", cls="error text-red-500 font-bold"),
                                                    cls="p-4 bg-red-50 border border-red-200 rounded"
                                                )
                                            raise
                                
                                # Call original function
                                return await endpoint(*args, **kwargs)
                            finally:
                                # Clean up auth context
                                clear_auth_context()
                        
                        # Use the wrapper instead of original endpoint
                        endpoint = async_state_injecting_wrapper
                    else:
                        @wraps(endpoint)
                        def sync_state_injecting_wrapper(*args, **kwargs):
                            try:
                                # Extract special FastHTML parameters
                                req = kwargs.get('req') or kwargs.get('request')
                                sess = kwargs.get('sess') or kwargs.get('session') or {}
                                auth = kwargs.get('auth')
                                
                                if not req:
                                    # Try to find request in args
                                    for arg in args:
                                        if isinstance(arg, Request):
                                            req = arg
                                            break
                                
                                if not req:
                                    raise ValueError("Request object not available for state injection")
                                
                                # Set auth context for the request
                                _setup_auth_context(auth, req, sess)
                                
                                # Inject state instances
                                for param_name, state_type in state_params:
                                    if param_name not in kwargs:
                                        try:
                                            state_instance = state_registry.resolve_state(state_type, req, sess, auth)
                                            kwargs[param_name] = state_instance
                                        except Exception as e:
                                            # Handle auth/permission errors gracefully
                                            if isinstance(e, (PermissionError, ValueError)):
                                                # Return error response
                                                from fasthtml.common import P, Div
                                                return Div(
                                                    P(f"Authentication Error: {str(e)}", cls="error text-red-500 font-bold"),
                                                    cls="p-4 bg-red-50 border border-red-200 rounded"
                                                )
                                            raise
                                
                                # Call original function
                                return endpoint(*args, **kwargs)
                            finally:
                                # Clean up auth context
                                clear_auth_context()
                        
                        # Use the wrapper instead of original endpoint
                        endpoint = sync_state_injecting_wrapper
            
            # Call original add_route with potentially wrapped endpoint
            return original_add_route(self, path, endpoint, *remaining_args, **kwargs)
        
        # Apply the patch
        FastHTML.add_route = enhanced_add_route
        
        print("✓ FastHTML DI integration successfully patched")
        return True
        
    except ImportError as e:
        print(f"✗ FastHTML not available for patching: {e}")
        return False
    except Exception as e:
        print(f"✗ Failed to patch FastHTML DI: {e}")
        return False


def _setup_auth_context(auth: str, req: Request, sess: dict):
    """
    Set up authentication context for the current request.
    
    This function sets the auth context that can be used by authentication
    decorators and state resolution logic.
    
    Args:
        auth: Authentication string from FastHTML
        req: Request object
        sess: Session dictionary
    """
    # Set basic auth
    set_current_auth(auth)
    
    if auth:
        # Set user ID (can be overridden by custom auth implementation)
        set_user_id(auth)
        
        # Load user permissions and roles from session or custom implementation
        # This is where you would integrate with your auth system
        user_permissions = sess.get(f'user_permissions_{auth}', [])
        user_roles = sess.get(f'user_roles_{auth}', [])
        
        set_user_permissions(user_permissions)
        set_user_roles(user_roles)


def initialize_faststate():
    """
    Initialize FastState integration with FastHTML.
    
    This function should be called once during application startup to
    enable automatic state injection via FastHTML's dependency injection system.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    print("Initializing FastState integration with FastHTML...")
    
    success = patch_fasthtml_for_state_injection()
    
    if success:
        print("🎉 FastState initialization complete!")
        print("State types will now be automatically injected into route functions.")
    else:
        print("❌ FastState initialization failed!")
        print("Manual state management will be required.")
    
    return success


def register_auth_provider(
    get_permissions_fn: Callable[[str], list[str]] = None,
    get_roles_fn: Callable[[str], list[str]] = None,
    get_user_id_fn: Callable[[str], str] = None
):
    """
    Register custom authentication provider functions.
    
    This allows you to integrate FastState with your existing authentication
    and authorization system.
    
    Args:
        get_permissions_fn: Function to get user permissions from auth string
        get_roles_fn: Function to get user roles from auth string  
        get_user_id_fn: Function to extract user ID from auth string
        
    Example:
        ```python
        def get_user_permissions(auth_string):
            user = User.get_by_username(auth_string)
            return [perm.name for perm in user.permissions]
        
        def get_user_roles(auth_string):
            user = User.get_by_username(auth_string)
            return [role.name for role in user.roles]
        
        register_auth_provider(
            get_permissions_fn=get_user_permissions,
            get_roles_fn=get_user_roles
        )
        ```
    """
    from . import auth
    
    if get_permissions_fn:
        auth._get_user_permissions_impl = get_permissions_fn
        print("✓ Custom permissions provider registered")
    
    if get_roles_fn:
        auth._get_user_roles_impl = get_roles_fn
        print("✓ Custom roles provider registered")
    
    if get_user_id_fn:
        auth._get_user_id_impl = get_user_id_fn
        print("✓ Custom user ID provider registered")


def create_state_middleware():
    """
    Create middleware for setting up state context in FastHTML applications.
    
    This middleware can be used as an alternative to the monkey patching approach
    for applications that prefer explicit middleware setup.
    
    Returns:
        Middleware function that can be added to FastHTML app
    """
    def state_middleware(request: Request, call_next):
        """Middleware that sets up state context for each request."""
        try:
            # Set up auth context from session
            auth = request.scope.get('auth')
            sess = getattr(request, 'session', {})
            
            _setup_auth_context(auth, request, sess)
            
            # Process request
            response = call_next(request)
            return response
        finally:
            # Clean up context
            clear_auth_context()
    
    return state_middleware


def get_state_info() -> dict:
    """
    Get information about registered states and current status.
    
    Useful for debugging and monitoring.
    
    Returns:
        Dictionary with state registry information
    """
    return {
        'registered_states': [
            {
                'class_name': cls.__name__,
                'scope': config.scope.value,
                'requires_auth': config.requires_auth,
                'permissions': config.permissions,
                'auto_persist': config.auto_persist,
                'ttl': config.ttl
            }
            for cls, config in state_registry._state_configs.items()
        ],
        'cached_instances': len(state_registry._state_instances),
        'integration_active': True  # Would check if patching was successful
    }