"""
Dependency Injection Container Configuration

🔧 Service Configuration:
This module provides configuration utilities for setting up the service container
with different service implementations based on application needs.
"""

from typing import Type, Optional
from .lifecycle.composition_entity import ServiceContainer, set_service_container
from .services.persistence_service import (
    PersistenceService, EntityPersistenceService, InMemoryPersistenceService
)
from .services.validation_service import (
    ValidationService, EntityValidationService, SimpleValidationService
)
from .services.event_service import (
    EventService, EntityEventService, SimpleEventService
)
from .services.signal_service import (
    SignalService, ReactiveSignalService, SimpleSignalService
)
from .services.metrics_service import (
    MetricsService, EntityMetricsService, SimpleMetricsService
)


class DIContainerBuilder:
    """
    Builder for configuring the dependency injection container.
    
    This builder provides a fluent interface for setting up all the services
    that entities need, making it easy to configure different environments.
    """
    
    def __init__(self):
        self.container = ServiceContainer()
    
    def with_persistence(self, service: PersistenceService) -> 'DIContainerBuilder':
        """Configure persistence service"""
        self.container.configure_persistence(service)
        return self
    
    def with_validation(self, service: ValidationService) -> 'DIContainerBuilder':
        """Configure validation service"""
        self.container.configure_validation(service)
        return self
    
    def with_events(self, service: EventService) -> 'DIContainerBuilder':
        """Configure event service"""
        self.container.configure_events(service)
        return self
    
    def with_signals(self, service: SignalService) -> 'DIContainerBuilder':
        """Configure signal service"""
        self.container.configure_signals(service)
        return self
    
    def with_metrics(self, service: MetricsService) -> 'DIContainerBuilder':
        """Configure metrics service"""
        self.container.configure_metrics(service)
        return self
    
    def build(self) -> ServiceContainer:
        """Build and return the configured container"""
        return self.container
    
    def install(self) -> ServiceContainer:
        """Build container and set it as the global container"""
        set_service_container(self.container)
        return self.container


def create_development_container() -> ServiceContainer:
    """
    Create a development-friendly container with full-featured services.
    
    This configuration provides comprehensive functionality for development
    and debugging while still being lightweight.
    """
    return (DIContainerBuilder()
            .with_persistence(InMemoryPersistenceService())
            .with_validation(EntityValidationService())
            .with_events(EntityEventService())
            .with_signals(ReactiveSignalService(use_namespace=True))
            .with_metrics(EntityMetricsService(retention_hours=24))
            .build())


def create_production_container(
    persistence_manager=None,
    event_dispatcher=None,
    use_namespaced_signals=True,
    metrics_retention_hours=168  # 1 week
) -> ServiceContainer:
    """
    Create a production-ready container with enterprise services.
    
    This configuration provides full functionality with production-grade services
    including proper persistence management and comprehensive metrics.
    """
    # Set up persistence service
    if persistence_manager:
        persistence_service = EntityPersistenceService(persistence_manager)
    else:
        persistence_service = InMemoryPersistenceService()
    
    # Set up event service
    if event_dispatcher:
        event_service = EntityEventService(event_dispatcher)
    else:
        event_service = EntityEventService()
    
    return (DIContainerBuilder()
            .with_persistence(persistence_service)
            .with_validation(EntityValidationService())
            .with_events(event_service)
            .with_signals(ReactiveSignalService(use_namespace=use_namespaced_signals))
            .with_metrics(EntityMetricsService(retention_hours=metrics_retention_hours))
            .build())


def create_testing_container() -> ServiceContainer:
    """
    Create a minimal container optimized for testing.
    
    This configuration uses simple, fast services that don't require
    external dependencies and are easy to reset between tests.
    """
    return (DIContainerBuilder()
            .with_persistence(InMemoryPersistenceService())
            .with_validation(SimpleValidationService())
            .with_events(SimpleEventService())
            .with_signals(SimpleSignalService())
            .with_metrics(SimpleMetricsService())
            .build())


def create_minimal_container() -> ServiceContainer:
    """
    Create the most minimal container possible.
    
    This configuration provides basic functionality with minimal overhead,
    perfect for simple applications or embedded use cases.
    """
    return (DIContainerBuilder()
            .with_persistence(InMemoryPersistenceService())
            .with_validation(SimpleValidationService())
            .with_events(SimpleEventService())
            .with_signals(SimpleSignalService())
            .with_metrics(SimpleMetricsService())
            .build())


def configure_for_environment(environment: str = "development") -> ServiceContainer:
    """
    Configure container based on environment name.
    
    This is a convenience function that sets up appropriate services
    based on the deployment environment.
    """
    if environment.lower() == "production":
        container = create_production_container()
    elif environment.lower() == "testing":
        container = create_testing_container()
    elif environment.lower() == "minimal":
        container = create_minimal_container()
    else:  # development
        container = create_development_container()
    
    # Install as global container
    set_service_container(container)
    return container


# Convenience functions for quick setup
def setup_development():
    """Quick setup for development environment"""
    return configure_for_environment("development")


def setup_production(**kwargs):
    """Quick setup for production environment"""
    container = create_production_container(**kwargs)
    set_service_container(container)
    return container


def setup_testing():
    """Quick setup for testing environment"""
    return configure_for_environment("testing")


# Export main components
__all__ = [
    "DIContainerBuilder",
    "create_development_container",
    "create_production_container", 
    "create_testing_container",
    "create_minimal_container",
    "configure_for_environment",
    "setup_development",
    "setup_production", 
    "setup_testing"
]