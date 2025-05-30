"""
FastState Authentication and Authorization System

This module provides authentication and authorization decorators and utilities
for controlling access to state operations and event handlers.
"""

from functools import wraps
from typing import Optional, List, Callable, Any
from contextvars import ContextVar


class AuthenticationError(Exception):
    """Raised when authentication is required but not provided."""
    pass


class AuthorizationError(Exception):
    """Raised when user lacks required permissions or roles."""
    pass


# Context variables for storing current request context
current_auth: ContextVar[Optional[str]] = ContextVar('current_auth', default=None)
current_user_permissions: ContextVar[List[str]] = ContextVar('current_user_permissions', default=[])
current_user_roles: ContextVar[List[str]] = ContextVar('current_user_roles', default=[])
current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)


def requires_auth(permissions: Optional[List[str]] = None, 
                 roles: Optional[List[str]] = None,
                 owner_only: bool = False):
    """
    Decorator for event methods requiring authentication/authorization.
    
    This decorator can be used in several ways:
    
    Basic authentication requirement:
    ```python
    @event
    @requires_auth()
    def update_profile(self, data: dict): ...
    ```
    
    With specific permissions:
    ```python
    @event
    @requires_auth(permissions=['admin.users'])
    def delete_user(self, user_id: int): ...
    ```
    
    With roles:
    ```python
    @event
    @requires_auth(roles=['admin', 'manager'])
    def manage_users(self): ...
    ```
    
    Owner-only access:
    ```python
    @event
    @requires_auth(owner_only=True)
    def update_my_data(self, data: dict): ...
    ```
    
    Combined requirements:
    ```python
    @event
    @requires_auth(permissions=['users.edit'], owner_only=True)
    def edit_profile(self, user_id: int, data: dict): ...
    ```
    
    Args:
        permissions: List of required permissions
        roles: List of required roles (user needs at least one)
        owner_only: If True, checks that state belongs to current user
        
    Returns:
        Decorated function with authentication/authorization checks
        
    Raises:
        AuthenticationError: If user is not authenticated
        AuthorizationError: If user lacks required permissions/roles/ownership
    """
    def decorator(func: Callable) -> Callable:
        import asyncio
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(self, *args, **kwargs):
                # Get current authentication context
                auth = get_current_auth()
                
                if not auth:
                    raise AuthenticationError("Authentication required")
                
                # Check permissions
                if permissions:
                    user_perms = get_user_permissions(auth)
                    if not any(perm in user_perms for perm in permissions):
                        raise AuthorizationError(f"Missing required permissions: {permissions}")
                
                # Check roles  
                if roles:
                    user_roles = get_user_roles(auth)
                    if not any(role in user_roles for role in roles):
                        raise AuthorizationError(f"Missing required roles: {roles}")
                
                # Check ownership
                if owner_only:
                    user_id = get_user_id(auth)
                    if hasattr(self, 'user_id'):
                        if self.user_id != user_id:
                            raise AuthorizationError("Access denied: owner only")
                    elif hasattr(self, 'owner_id'):
                        if self.owner_id != user_id:
                            raise AuthorizationError("Access denied: owner only")
                
                # Call original function
                return await func(self, *args, **kwargs)
            
            # Store auth requirements on the function for introspection
            async_wrapper._auth_config = {
                'required': True,
                'permissions': permissions or [],
                'roles': roles or [],
                'owner_only': owner_only
            }
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(self, *args, **kwargs):
                # Get current authentication context
                auth = get_current_auth()
                
                if not auth:
                    raise AuthenticationError("Authentication required")
                
                # Check permissions
                if permissions:
                    user_perms = get_user_permissions(auth)
                    if not any(perm in user_perms for perm in permissions):
                        raise AuthorizationError(f"Missing required permissions: {permissions}")
                
                # Check roles  
                if roles:
                    user_roles = get_user_roles(auth)
                    if not any(role in user_roles for role in roles):
                        raise AuthorizationError(f"Missing required roles: {roles}")
                
                # Check ownership
                if owner_only:
                    user_id = get_user_id(auth)
                    if hasattr(self, 'user_id'):
                        if self.user_id != user_id:
                            raise AuthorizationError("Access denied: owner only")
                    elif hasattr(self, 'owner_id'):
                        if self.owner_id != user_id:
                            raise AuthorizationError("Access denied: owner only")
                
                # Call original function
                return func(self, *args, **kwargs)
            
            # Store auth requirements on the function for introspection
            sync_wrapper._auth_config = {
                'required': True,
                'permissions': permissions or [],
                'roles': roles or [],
                'owner_only': owner_only
            }
            
            return sync_wrapper
    return decorator


def get_current_auth() -> Optional[str]:
    """
    Get current authentication string from context.
    
    This function retrieves the authentication information for the current request.
    The auth string typically contains a username, user ID, or similar identifier.
    
    Returns:
        Authentication string if user is authenticated, None otherwise
    """
    return current_auth.get()


def set_current_auth(auth: Optional[str]):
    """
    Set current authentication string in context.
    
    This is typically called by FastHTML middleware or beforeware to set
    the authentication context for the current request.
    
    Args:
        auth: Authentication string (username, user_id, etc.)
    """
    current_auth.set(auth)


def get_user_permissions(auth: str) -> List[str]:
    """
    Get user permissions based on authentication string.
    
    This function can be customized to integrate with your permission system.
    The default implementation uses context variables that can be set by
    your authentication middleware.
    
    Args:
        auth: Authentication string
        
    Returns:
        List of permission strings the user has
    """
    # Try to get from context first
    perms = current_user_permissions.get()
    if perms:
        return perms
    
    # Fallback to custom implementation
    return _get_user_permissions_impl(auth)


def set_user_permissions(permissions: List[str]):
    """
    Set user permissions in context.
    
    Args:
        permissions: List of permission strings
    """
    current_user_permissions.set(permissions)


def get_user_roles(auth: str) -> List[str]:
    """
    Get user roles based on authentication string.
    
    This function can be customized to integrate with your role system.
    The default implementation uses context variables that can be set by
    your authentication middleware.
    
    Args:
        auth: Authentication string
        
    Returns:
        List of role strings the user has
    """
    # Try to get from context first
    roles = current_user_roles.get()
    if roles:
        return roles
    
    # Fallback to custom implementation
    return _get_user_roles_impl(auth)


def set_user_roles(roles: List[str]):
    """
    Set user roles in context.
    
    Args:
        roles: List of role strings
    """
    current_user_roles.set(roles)


def get_user_id(auth: str) -> Optional[str]:
    """
    Extract user ID from authentication string.
    
    This function can be customized based on your authentication format.
    
    Args:
        auth: Authentication string
        
    Returns:
        User ID string
    """
    # Try to get from context first
    user_id = current_user_id.get()
    if user_id:
        return user_id
    
    # Fallback to custom implementation
    return _get_user_id_impl(auth)


def set_user_id(user_id: Optional[str]):
    """
    Set user ID in context.
    
    Args:
        user_id: User ID string
    """
    current_user_id.set(user_id)


def clear_auth_context():
    """Clear all authentication context variables."""
    current_auth.set(None)
    current_user_permissions.set([])
    current_user_roles.set([])
    current_user_id.set(None)


# Default implementations that can be overridden
def _get_user_permissions_impl(auth: str) -> List[str]:
    """
    Default implementation for getting user permissions.
    
    Override this function to integrate with your permission system.
    
    Args:
        auth: Authentication string
        
    Returns:
        List of permissions
    """
    # TODO: Implement based on your permission system
    # Example implementations:
    # - Query database for user permissions
    # - Parse JWT token for permissions
    # - Call external auth service
    # - Use cached permissions from session
    
    # For now, return empty list
    return []


def _get_user_roles_impl(auth: str) -> List[str]:
    """
    Default implementation for getting user roles.
    
    Override this function to integrate with your role system.
    
    Args:
        auth: Authentication string
        
    Returns:
        List of roles
    """
    # TODO: Implement based on your role system
    # Example implementations:
    # - Query database for user roles
    # - Parse JWT token for roles
    # - Call external auth service
    # - Use cached roles from session
    
    # For now, return empty list
    return []


def _get_user_id_impl(auth: str) -> Optional[str]:
    """
    Default implementation for extracting user ID from auth string.
    
    Override this function based on your authentication format.
    
    Args:
        auth: Authentication string
        
    Returns:
        User ID or None
    """
    # TODO: Implement based on your auth format
    # Example implementations:
    # - Return auth string directly if it's already a user ID
    # - Parse username and look up user ID
    # - Extract user ID from JWT token
    # - Parse structured auth string
    
    # For now, assume auth string is the user ID
    return auth


def has_permission(permission: str, auth: Optional[str] = None) -> bool:
    """
    Check if current user has a specific permission.
    
    Args:
        permission: Permission string to check
        auth: Authentication string (uses current context if not provided)
        
    Returns:
        True if user has the permission
    """
    if auth is None:
        auth = get_current_auth()
    
    if not auth:
        return False
    
    user_perms = get_user_permissions(auth)
    return permission in user_perms


def has_role(role: str, auth: Optional[str] = None) -> bool:
    """
    Check if current user has a specific role.
    
    Args:
        role: Role string to check
        auth: Authentication string (uses current context if not provided)
        
    Returns:
        True if user has the role
    """
    if auth is None:
        auth = get_current_auth()
    
    if not auth:
        return False
    
    user_roles = get_user_roles(auth)
    return role in user_roles


def is_authenticated(auth: Optional[str] = None) -> bool:
    """
    Check if user is authenticated.
    
    Args:
        auth: Authentication string (uses current context if not provided)
        
    Returns:
        True if user is authenticated
    """
    if auth is None:
        auth = get_current_auth()
    
    return auth is not None


# Utility functions for common auth patterns
def require_admin(func: Callable) -> Callable:
    """Shorthand decorator for requiring admin role."""
    return requires_auth(roles=['admin'])(func)


def require_authenticated(func: Callable) -> Callable:
    """Shorthand decorator for requiring authentication only."""
    return requires_auth()(func)