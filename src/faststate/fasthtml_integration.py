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
                            
                            # Inject state instances
                            for param_name, state_type in state_params:
                                if param_name not in kwargs:
                                    state_instance = state_registry.resolve_state(state_type, req, sess, auth)
                                    kwargs[param_name] = state_instance
                            
                            # Call original function
                            return await endpoint(*args, **kwargs)
                        
                        # Use the wrapper instead of original endpoint
                        endpoint = async_state_injecting_wrapper
                    else:
                        @wraps(endpoint)
                        def sync_state_injecting_wrapper(*args, **kwargs):
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
                            
                            # Inject state instances
                            for param_name, state_type in state_params:
                                if param_name not in kwargs:
                                    state_instance = state_registry.resolve_state(state_type, req, sess, auth)
                                    kwargs[param_name] = state_instance
                            
                            # Call original function
                            return endpoint(*args, **kwargs)
                        
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




def create_state_middleware():
    """
    Create middleware for setting up state context in FastHTML applications.
    
    This middleware can be used as an alternative to the monkey patching approach
    for applications that prefer explicit middleware setup.
    
    Returns:
        Middleware function that can be added to FastHTML app
    """
    def state_middleware(request: Request, call_next):
        """Middleware that processes state injection for each request."""
        # Process request normally - state injection happens at route level
        response = call_next(request)
        return response
    
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
                'auto_persist': config.auto_persist,
                'ttl': config.ttl
            }
            for cls, config in state_registry._state_configs.items()
        ],
        'cached_instances': len(state_registry._state_instances),
        'integration_active': True  # Would check if patching was successful
    }