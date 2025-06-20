"""
Dependency Injection Container

🔧 Service Composition and Lifecycle:
The DI container manages service registration, instantiation, and lifecycle
while maintaining clean architecture principles and supporting configuration-driven
service composition.
"""

import asyncio
import inspect
from typing import (
    Any, Dict, Optional, Type, TypeVar, Callable, Union,
    get_type_hints, get_origin, get_args
)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import weakref

T = TypeVar('T')

class ServiceScope(Enum):
    """Service lifetime scopes"""
    SINGLETON = "singleton"      # One instance for entire application
    TRANSIENT = "transient"      # New instance every time
    SCOPED = "scoped"           # One instance per scope (e.g., per request)

class DIError(Exception):
    """Base exception for dependency injection errors"""
    pass

class ServiceNotFoundError(DIError):
    """Raised when a service is not registered"""
    pass

class CircularDependencyError(DIError):
    """Raised when circular dependencies are detected"""
    pass

class ServiceConfigurationError(DIError):
    """Raised when service configuration is invalid"""
    pass

@dataclass
class ServiceRegistration:
    """Service registration information"""
    service_type: Type
    implementation: Union[Type, Callable, Any]
    scope: ServiceScope = ServiceScope.SINGLETON
    factory: Optional[Callable] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    lazy: bool = True
    registered_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate registration after creation"""
        if self.factory and not callable(self.factory):
            raise ServiceConfigurationError("Factory must be callable")
        
        if not self.factory and not (inspect.isclass(self.implementation) or callable(self.implementation)):
            raise ServiceConfigurationError("Implementation must be a class or callable")

class ServiceInstance:
    """Wrapper for service instances with metadata"""
    
    def __init__(self, instance: Any, registration: ServiceRegistration):
        self.instance = instance
        self.registration = registration
        self.created_at = datetime.now()
        self.access_count = 0
        self.last_accessed = datetime.now()
    
    def access(self) -> Any:
        """Access the service instance"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.instance

class DIContainer:
    """
    Dependency Injection Container for StarModel.
    
    Provides service registration, resolution, and lifecycle management
    with support for different scopes and automatic dependency injection.
    
    Features:
    - Multiple service scopes (singleton, transient, scoped)
    - Automatic constructor injection
    - Factory method support
    - Circular dependency detection
    - Service configuration
    - Lazy loading
    """
    
    def __init__(self):
        self._registrations: Dict[str, ServiceRegistration] = {}
        self._singletons: Dict[str, ServiceInstance] = {}
        self._scoped_instances: Dict[str, Dict[str, ServiceInstance]] = {}
        self._resolution_stack: list = []
        
        # Service discovery
        self._service_aliases: Dict[str, str] = {}
        self._interface_implementations: Dict[Type, List[str]] = {}
        
        # Lifecycle management
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._is_started = False
        self._is_shutdown = False
    
    def register(
        self,
        service_type: Union[Type[T], str],
        implementation: Union[Type[T], Callable[[], T], T, None] = None,
        scope: ServiceScope = ServiceScope.SINGLETON,
        factory: Optional[Callable] = None,
        config: Optional[Dict[str, Any]] = None,
        lazy: bool = True,
        alias: Optional[str] = None
    ) -> 'DIContainer':
        """
        Register a service with the container.
        
        Args:
            service_type: The service type or string key
            implementation: The implementation class, instance, or factory
            scope: Service lifetime scope
            factory: Optional factory function
            config: Service configuration
            lazy: Whether to defer instantiation
            alias: Optional alias for the service
            
        Returns:
            Self for method chaining
        """
        if self._is_shutdown:
            raise DIError("Cannot register services after shutdown")
        
        # Normalize service key
        service_key = self._get_service_key(service_type)
        
        # Auto-detect implementation if not provided
        if implementation is None:
            if isinstance(service_type, type):
                implementation = service_type
            else:
                raise ServiceConfigurationError(f"Implementation required for string key: {service_key}")
        
        # Create registration
        registration = ServiceRegistration(
            service_type=service_type if isinstance(service_type, type) else type(implementation),
            implementation=implementation,
            scope=scope,
            factory=factory,
            config=config or {},
            lazy=lazy
        )
        
        # Analyze dependencies
        registration.dependencies = self._analyze_dependencies(implementation)
        
        # Store registration
        self._registrations[service_key] = registration
        
        # Handle alias
        if alias:
            self._service_aliases[alias] = service_key
        
        # Update interface mappings
        if isinstance(service_type, type):
            self._update_interface_mappings(service_type, service_key)
        
        return self
    
    def register_singleton(self, service_type: Union[Type[T], str], implementation: Union[Type[T], T, Callable[[], T]]) -> 'DIContainer':
        """Register a singleton service"""
        return self.register(service_type, implementation, ServiceScope.SINGLETON)
    
    def register_transient(self, service_type: Union[Type[T], str], implementation: Union[Type[T], Callable[[], T]]) -> 'DIContainer':
        """Register a transient service"""
        return self.register(service_type, implementation, ServiceScope.TRANSIENT)
    
    def register_factory(self, service_type: Union[Type[T], str], factory: Callable[[], T]) -> 'DIContainer':
        """Register a service with a factory function"""
        return self.register(service_type, None, factory=factory)
    
    def get(self, service_type: Union[Type[T], str], scope_id: Optional[str] = None) -> T:
        """
        Get a service instance.
        
        Args:
            service_type: The service type or string key
            scope_id: Optional scope identifier for scoped services
            
        Returns:
            The service instance
        """
        if self._is_shutdown:
            raise DIError("Container is shut down")
        
        service_key = self._resolve_service_key(service_type)
        
        if service_key not in self._registrations:
            raise ServiceNotFoundError(f"Service not registered: {service_key}")
        
        registration = self._registrations[service_key]
        
        # Check for circular dependencies
        if service_key in self._resolution_stack:
            cycle = " -> ".join(self._resolution_stack + [service_key])
            raise CircularDependencyError(f"Circular dependency detected: {cycle}")
        
        try:
            self._resolution_stack.append(service_key)
            
            if registration.scope == ServiceScope.SINGLETON:
                return self._get_singleton(service_key, registration)
            elif registration.scope == ServiceScope.TRANSIENT:
                return self._create_instance(registration)
            elif registration.scope == ServiceScope.SCOPED:
                return self._get_scoped(service_key, registration, scope_id or "default")
            else:
                raise ServiceConfigurationError(f"Unknown scope: {registration.scope}")
        
        finally:
            self._resolution_stack.pop()
    
    def try_get(self, service_type: Union[Type[T], str]) -> Optional[T]:
        """Try to get a service, returning None if not found"""
        try:
            return self.get(service_type)
        except ServiceNotFoundError:
            return None
    
    def is_registered(self, service_type: Union[Type[T], str]) -> bool:
        """Check if a service is registered"""
        service_key = self._resolve_service_key(service_type)
        return service_key in self._registrations
    
    def configure(self, config_dict: Dict[str, Any]):
        """Configure services from dictionary"""
        for service_key, service_config in config_dict.items():
            if service_key in self._registrations:
                registration = self._registrations[service_key]
                registration.config.update(service_config)
    
    def add_startup_hook(self, hook: Callable):
        """Add a startup hook"""
        self._startup_hooks.append(hook)
    
    def add_shutdown_hook(self, hook: Callable):
        """Add a shutdown hook"""
        self._shutdown_hooks.append(hook)
    
    async def startup(self):
        """Start the container and run startup hooks"""
        if self._is_started:
            return
        
        # Initialize eager singletons
        for service_key, registration in self._registrations.items():
            if registration.scope == ServiceScope.SINGLETON and not registration.lazy:
                self.get(service_key)
        
        # Run startup hooks
        for hook in self._startup_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook()
            else:
                hook()
        
        self._is_started = True
    
    async def shutdown(self):
        """Shutdown the container and run shutdown hooks"""
        if self._is_shutdown:
            return
        
        # Run shutdown hooks
        for hook in reversed(self._shutdown_hooks):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception:
                # Log but don't fail shutdown
                pass
        
        # Dispose singletons that support it
        for instance_wrapper in self._singletons.values():
            instance = instance_wrapper.instance
            if hasattr(instance, 'dispose'):
                try:
                    if asyncio.iscoroutinefunction(instance.dispose):
                        await instance.dispose()
                    else:
                        instance.dispose()
                except Exception:
                    pass
        
        # Clear all instances
        self._singletons.clear()
        self._scoped_instances.clear()
        
        self._is_shutdown = True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get container metrics"""
        singleton_count = len(self._singletons)
        scoped_count = sum(len(scope_instances) for scope_instances in self._scoped_instances.values())
        
        # Calculate access stats
        total_accesses = sum(instance.access_count for instance in self._singletons.values())
        
        return {
            "registered_services": len(self._registrations),
            "singleton_instances": singleton_count,
            "scoped_instances": scoped_count,
            "total_accesses": total_accesses,
            "is_started": self._is_started,
            "is_shutdown": self._is_shutdown,
            "service_aliases": len(self._service_aliases)
        }
    
    def _get_service_key(self, service_type: Union[Type, str]) -> str:
        """Get normalized service key"""
        if isinstance(service_type, str):
            return service_type
        elif isinstance(service_type, type):
            return f"{service_type.__module__}.{service_type.__name__}"
        else:
            return str(service_type)
    
    def _resolve_service_key(self, service_type: Union[Type, str]) -> str:
        """Resolve service key, handling aliases"""
        service_key = self._get_service_key(service_type)
        
        # Check aliases
        if service_key in self._service_aliases:
            return self._service_aliases[service_key]
        
        return service_key
    
    def _analyze_dependencies(self, implementation: Any) -> Dict[str, str]:
        """Analyze constructor dependencies"""
        dependencies = {}
        
        if not inspect.isclass(implementation):
            return dependencies
        
        # Get constructor signature
        try:
            constructor = implementation.__init__
            signature = inspect.signature(constructor)
            type_hints = get_type_hints(constructor)
            
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue
                
                # Get type hint
                if param_name in type_hints:
                    param_type = type_hints[param_name]
                    dependencies[param_name] = self._get_service_key(param_type)
        
        except Exception:
            # If we can't analyze, that's ok
            pass
        
        return dependencies
    
    def _get_singleton(self, service_key: str, registration: ServiceRegistration) -> Any:
        """Get or create singleton instance"""
        if service_key not in self._singletons:
            instance = self._create_instance(registration)
            self._singletons[service_key] = ServiceInstance(instance, registration)
        
        return self._singletons[service_key].access()
    
    def _get_scoped(self, service_key: str, registration: ServiceRegistration, scope_id: str) -> Any:
        """Get or create scoped instance"""
        if scope_id not in self._scoped_instances:
            self._scoped_instances[scope_id] = {}
        
        scope_instances = self._scoped_instances[scope_id]
        
        if service_key not in scope_instances:
            instance = self._create_instance(registration)
            scope_instances[service_key] = ServiceInstance(instance, registration)
        
        return scope_instances[service_key].access()
    
    def _create_instance(self, registration: ServiceRegistration) -> Any:
        """Create a new service instance"""
        if registration.factory:
            # Use factory
            return self._invoke_factory(registration.factory, registration.config)
        
        elif inspect.isclass(registration.implementation):
            # Instantiate class with dependency injection
            return self._instantiate_class(registration.implementation, registration.config)
        
        elif callable(registration.implementation):
            # Call factory function
            return self._invoke_factory(registration.implementation, registration.config)
        
        else:
            # Return instance as-is
            return registration.implementation
    
    def _instantiate_class(self, cls: Type, config: Dict[str, Any]) -> Any:
        """Instantiate class with dependency injection"""
        constructor = cls.__init__
        signature = inspect.signature(constructor)
        
        kwargs = {}
        
        # Add config parameters
        kwargs.update(config)
        
        # Inject dependencies
        for param_name, param in signature.parameters.items():
            if param_name == 'self' or param_name in kwargs:
                continue
            
            # Try to resolve dependency
            try:
                param_type = param.annotation
                if param_type != inspect.Parameter.empty:
                    dependency = self.get(param_type)
                    kwargs[param_name] = dependency
            except (ServiceNotFoundError, TypeError):
                # If we can't resolve and no default, this will fail at instantiation
                pass
        
        return cls(**kwargs)
    
    def _invoke_factory(self, factory: Callable, config: Dict[str, Any]) -> Any:
        """Invoke factory with dependency injection"""
        signature = inspect.signature(factory)
        kwargs = {}
        
        # Add config parameters
        kwargs.update(config)
        
        # Inject dependencies
        for param_name, param in signature.parameters.items():
            if param_name in kwargs:
                continue
            
            try:
                param_type = param.annotation
                if param_type != inspect.Parameter.empty:
                    dependency = self.get(param_type)
                    kwargs[param_name] = dependency
            except (ServiceNotFoundError, TypeError):
                pass
        
        return factory(**kwargs)
    
    def _update_interface_mappings(self, service_type: Type, service_key: str):
        """Update interface to implementation mappings"""
        # This could be enhanced to track interfaces and their implementations
        # for more sophisticated service discovery
        pass

# Global container management
_current_container: Optional[DIContainer] = None

def set_current_container(container: DIContainer):
    """Set the current global container"""
    global _current_container
    _current_container = container

def get_current_container() -> Optional[DIContainer]:
    """Get the current global container"""
    return _current_container

def clear_current_container():
    """Clear the current global container"""
    global _current_container
    _current_container = None

# Export main components
__all__ = [
    "DIContainer", "ServiceScope", "ServiceRegistration", "ServiceInstance",
    "DIError", "ServiceNotFoundError", "CircularDependencyError", "ServiceConfigurationError",
    "set_current_container", "get_current_container", "clear_current_container"
]