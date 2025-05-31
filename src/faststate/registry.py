"""
FastState Registry System

This module provides the core state configuration and registry system that manages
different state scopes and configurations for automatic dependency injection.
"""

from typing import Type, Dict, Any, Optional, get_origin, get_args, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field
from fasthtml.common import Request

if TYPE_CHECKING:
    from .state import ReactiveState


class StateScope(Enum):
    """Enumeration of different state scopes supported by FastState."""
    GLOBAL = "global"        # Shared across all users
    SESSION = "session"      # Per user session (current default)
    USER = "user"           # Per authenticated user across sessions
    COMPONENT = "component"  # Per component instance
    RECORD = "record"       # Tied to specific database record


@dataclass
class StateConfig:
    """Configuration for a state class defining its scope and persistence."""
    scope: StateScope = StateScope.SESSION
    ttl: Optional[int] = None  # Time to live in seconds
    auto_persist: bool = False
    persistence_backend: Optional[str] = None  # Name of persistence backend to use


class FastStateRegistry:
    """
    Registry for state types that can be automatically injected via FastHTML's DI system.
    
    This class manages state type registration, instance caching, and scope-based resolution.
    """
    
    def __init__(self):
        self._state_configs: Dict[Type, StateConfig] = {}
        self._state_instances: Dict[str, 'ReactiveState'] = {}
    
    def register(self, state_cls: Type['ReactiveState'], config: StateConfig):
        """
        Register a state class for automatic dependency injection.
        
        Args:
            state_cls: The ReactiveState subclass to register
            config: Configuration defining scope, persistence, etc.
        """
        self._state_configs[state_cls] = config
    
    def is_state_type(self, annotation: Any) -> bool:
        """
        Check if a type annotation represents a registered state type.
        
        Handles generic types like Optional[StateType].
        
        Args:
            annotation: Type annotation to check
            
        Returns:
            True if annotation is a registered state type
        """
        # Handle generic types like Optional[StateType]
        origin = get_origin(annotation)
        if origin is not None:
            args = get_args(annotation)
            if args:
                annotation = args[0]  # Extract actual type from Optional[Type]
        
        return annotation in self._state_configs
    
    async def resolve_state(self, state_cls: Type, req: Request, sess: dict, auth: Optional[str] = None) -> 'ReactiveState':
        """
        Resolve state instance based on registered configuration.
        
        Args:
            state_cls: The state class to resolve
            req: FastHTML request object
            sess: Session dictionary
            auth: Authentication string (optional, for USER scope)
            
        Returns:
            State instance for the given scope and context
            
        Raises:
            ValueError: If required parameters are missing
        """
        config = self._state_configs[state_cls]
        
        # Generate state key
        state_key = self._generate_state_key(state_cls, config, req, sess, auth)
        
        # Return cached instance if available
        if state_key in self._state_instances:
            return self._state_instances[state_key]
        
        # Try to load from persistence if enabled
        state = None
        if config.auto_persist and config.persistence_backend:
            state = await self._load_from_persistence(state_cls, state_key, config)
        
        # Create new instance if not found in persistence
        if state is None:
            state = self._create_state_instance(state_cls, config, req, sess, auth)
        
        # Cache the instance
        self._state_instances[state_key] = state
        
        # Save to persistence if auto_persist is enabled and this is a new instance
        if config.auto_persist and config.persistence_backend:
            await self._save_to_persistence(state, state_key, config)
        
        # Maintain compatibility with existing session storage
        if config.scope == StateScope.SESSION:
            sess[f"{state_cls.__name__}_id"] = state.id
            
        return state
    
    def _generate_state_key(self, state_cls: Type, config: StateConfig, 
                           req: Request, sess: dict, auth: Optional[str]) -> str:
        """
        Generate hierarchical state key based on scope.
        
        Args:
            state_cls: State class type
            config: State configuration
            req: Request object
            sess: Session dictionary
            auth: Authentication string
            
        Returns:
            Hierarchical state key string
            
        Raises:
            ValueError: If required parameters for scope are missing
        """
        class_name = state_cls.__name__
        
        match config.scope:
            case StateScope.GLOBAL:
                return f"global:{class_name}"
            
            case StateScope.SESSION:
                session_id = sess.get('session_id') or str(id(sess))
                return f"session:{session_id}:{class_name}"
            
            case StateScope.USER:
                if not auth:
                    raise ValueError(f"User-scoped state {class_name} requires authentication")
                return f"user:{auth}:{class_name}"
            
            case StateScope.COMPONENT:
                component_id = req.query_params.get('component_id')
                if not component_id:
                    raise ValueError(f"Component-scoped state {class_name} requires component_id parameter")
                session_id = sess.get('session_id') or str(id(sess))
                return f"component:{session_id}:{component_id}:{class_name}"
            
            case StateScope.RECORD:
                # Check both query params and path params for record_id
                record_id = (req.query_params.get('record_id') or 
                           req.path_params.get('record_id') or
                           req.query_params.get('id') or
                           req.path_params.get('id'))
                if not record_id:
                    raise ValueError(f"Record-scoped state {class_name} requires record_id parameter")
                return f"record:{class_name}:{record_id}"
            
            case _:
                raise ValueError(f"Unknown scope: {config.scope}")
    
    def _create_state_instance(self, state_cls: Type, config: StateConfig,
                              req: Request, sess: dict, auth: Optional[str]) -> 'ReactiveState':
        """
        Create new state instance, optionally loading from persistence.
        
        Args:
            state_cls: State class to instantiate
            config: State configuration
            req: Request object
            sess: Session dictionary
            auth: Authentication string
            
        Returns:
            New state instance
        """
        if config.scope == StateScope.RECORD:
            # For record-scoped states, try to load from database first
            record_id = (req.query_params.get('record_id') or 
                        req.path_params.get('record_id') or
                        req.query_params.get('id') or
                        req.path_params.get('id'))
            
            if config.auto_persist and record_id:
                existing_state = self._load_from_persistence(state_cls, record_id)
                if existing_state:
                    return existing_state
        
        # Create new instance
        return state_cls()
    
    async def _load_from_persistence(self, state_cls: Type, state_key: str, config: StateConfig) -> Optional['ReactiveState']:
        """
        Load state from persistence layer.
        
        Args:
            state_cls: State class type
            state_key: State key to load
            config: State configuration
            
        Returns:
            Loaded state instance or None
        """
        try:
            from .persistence import persistence_manager
            
            backend_name = config.persistence_backend or "default"
            state_data = await persistence_manager.load_state(state_key, backend_name)
            
            if state_data:
                # Create instance and populate with loaded data
                state = state_cls()
                for field_name, value in state_data.items():
                    if hasattr(state, field_name):
                        setattr(state, field_name, value)
                return state
                
        except ImportError:
            pass
        
        return None
    
    async def _save_to_persistence(self, state: 'ReactiveState', state_key: str, config: StateConfig) -> bool:
        """
        Save state to persistence layer.
        
        Args:
            state: State instance to save
            state_key: State key for storage
            config: State configuration
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            from .persistence import persistence_manager
            
            backend_name = config.persistence_backend or "default"
            state_data = state.model_dump()
            
            return await persistence_manager.save_state(
                state_key, 
                state_data, 
                ttl=config.ttl,
                backend=backend_name
            )
            
        except ImportError:
            pass
        
        return False
    
    
    def get_config(self, state_cls: Type) -> Optional[StateConfig]:
        """
        Get configuration for a registered state class.
        
        Args:
            state_cls: State class to get config for
            
        Returns:
            StateConfig if registered, None otherwise
        """
        return self._state_configs.get(state_cls)
    
    def clear_instance_cache(self):
        """Clear all cached state instances. Useful for testing."""
        self._state_instances.clear()
    
    def get_cached_instances(self) -> Dict[str, 'ReactiveState']:
        """Get all cached state instances. Useful for debugging."""
        return self._state_instances.copy()


# Global registry instance
state_registry = FastStateRegistry()