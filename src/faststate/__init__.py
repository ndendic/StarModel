"""
FastState - Reactive State Management for FastHTML

A powerful state management system that integrates with FastHTML's dependency injection
to provide automatic state management with scoping, authentication, and real-time updates.
"""

from .state import ReactiveState, event, _get_state
from .registry import StateScope, StateConfig, FastStateRegistry, state_registry
from .auth import (
    requires_auth, AuthenticationError, AuthorizationError,
    get_current_auth, set_current_auth, get_user_permissions, get_user_roles,
    get_user_id, set_user_permissions, set_user_roles, set_user_id,
    clear_auth_context, has_permission, has_role, is_authenticated,
    require_admin, require_authenticated
)

__all__ = [
    # Core state components
    'ReactiveState',
    'event',
    '_get_state',
    
    # Registry system
    'StateScope',
    'StateConfig', 
    'FastStateRegistry',
    'state_registry',
    
    # Authentication system
    'requires_auth',
    'AuthenticationError',
    'AuthorizationError',
    'get_current_auth',
    'set_current_auth',
    'get_user_permissions',
    'get_user_roles',
    'get_user_id',
    'set_user_permissions',
    'set_user_roles', 
    'set_user_id',
    'clear_auth_context',
    'has_permission',
    'has_role',
    'is_authenticated',
    'require_admin',
    'require_authenticated',
]

def hello() -> str:
    return "Hello from faststate!"
