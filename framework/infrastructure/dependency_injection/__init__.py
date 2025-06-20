"""
Dependency Injection - Service Configuration and Wiring

🔧 Clean Service Management:
This module provides dependency injection infrastructure for StarModel,
enabling clean separation of concerns and configurable service composition.

Components:
- DIContainer: Main dependency injection container
- ServiceRegistry: Service registration and lifecycle
- Configuration: Service configuration management
- Scopes: Service lifetime management
"""

from .container import (
    DIContainer, ServiceScope, set_current_container, 
    get_current_container, clear_current_container
)
from .registry import ServiceRegistry, ServiceConfig
from .configuration import ApplicationConfig, ConfigurationManager

# Global container instance
_container = DIContainer()

def get_container() -> DIContainer:
    """Get the global DI container"""
    return _container

def configure_services(config: ApplicationConfig):
    """Configure services in the global container"""
    _container.configure(config)

# Convenience functions for common services
def get_event_bus():
    """Get the configured event bus"""
    return _container.get('EventBus')

def get_persistence_manager():
    """Get the configured persistence manager"""
    return _container.get('PersistenceManager')

def get_event_dispatcher():
    """Get the configured event dispatcher"""
    return _container.get('EventDispatcher')

__all__ = [
    "DIContainer", "ServiceScope", "ServiceRegistry", "ServiceConfig",
    "ApplicationConfig", "ConfigurationManager",
    "get_container", "configure_services", 
    "get_event_bus", "get_persistence_manager", "get_event_dispatcher",
    "set_current_container", "get_current_container", "clear_current_container"
]