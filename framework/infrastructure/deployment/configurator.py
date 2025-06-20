"""
StarModel Application Configurator

🚀 Complete Application Setup with Clean Architecture:
This module provides the main configuration entry point for StarModel applications,
wiring together all the clean architecture components with proper dependency injection.
"""

from typing import List, Optional, Type, Any, Dict
import asyncio

# Import from screaming architecture
from ...entities.lifecycle.entity import Entity
from ...events.dispatching.dispatcher import EventDispatcher
from ...events.streaming.event_bus import InProcessEventBus, EventBus
from ...persistence.transactions.unit_of_work import UnitOfWork
from ...infrastructure.dependency_injection import DIContainer, ApplicationConfig, get_config

class StarModelConfigurator:
    """
    Main configurator for StarModel applications.
    
    Handles the complete setup of clean architecture components:
    - Dependency injection container
    - Event dispatcher
    - Event bus
    - Unit of Work
    - Persistence layer
    - Web adapters
    """
    
    def __init__(self, config: Optional[ApplicationConfig] = None):
        self.config = config or get_config()
        self.container = DIContainer()
        self._entities: List[Type[Entity]] = []
        self._is_configured = False
    
    def add_entity(self, entity_class: Type[Entity]) -> 'StarModelConfigurator':
        """Add an entity class to the application"""
        self._entities.append(entity_class)
        return self
    
    def add_entities(self, entity_classes: List[Type[Entity]]) -> 'StarModelConfigurator':
        """Add multiple entity classes to the application"""
        self._entities.extend(entity_classes)
        return self
    
    async def configure(self) -> DIContainer:
        """Configure all StarModel components with clean architecture"""
        if self._is_configured:
            return self.container
        
        # 1. Configure core services
        await self._configure_event_bus()
        await self._configure_persistence()
        await self._configure_dispatcher()
        await self._configure_unit_of_work()
        
        # 2. Register entities
        await self._register_entities()
        
        # 3. Configure web layer (if needed)
        await self._configure_web_layer()
        
        # 4. Start container
        await self.container.startup()
        
        # 5. Set as global container
        from ...infrastructure.dependency_injection.container import set_current_container
        set_current_container(self.container)
        
        self._is_configured = True
        return self.container
    
    async def _configure_event_bus(self):
        """Configure the event bus"""
        event_bus_config = self.config.event_bus
        
        # Register event bus based on configuration
        if event_bus_config.implementation == "InProcessEventBus":
            self.container.register_singleton(
                EventBus,
                lambda: InProcessEventBus(
                    max_concurrent_handlers=event_bus_config.max_concurrent_handlers
                )
            )
        else:
            # Could add support for Redis/RabbitMQ event buses here
            raise ValueError(f"Unsupported event bus: {event_bus_config.implementation}")
    
    async def _configure_persistence(self):
        """Configure the persistence layer"""
        persistence_config = self.config.persistence
        
        # Create and configure backend registry
        from ...persistence.repositories.manager import BackendRegistry, BackendConfig, PersistenceManager
        from ...entities.configuration.store import EntityStore
        
        registry = BackendRegistry()
        
        # Configure backends based on configuration
        for backend_name, backend_config in persistence_config.backends.items():
            if backend_name == "memory":
                registry.register_backend(
                    EntityStore.SERVER_MEMORY,
                    BackendConfig(
                        backend_type="memory",
                        implementation_class="framework.persistence.backends.memory.MemoryRepository",
                        config=backend_config,
                        enabled=True
                    )
                )
            elif backend_name == "sql":
                registry.register_backend(
                    EntityStore.SERVER_SQL,
                    BackendConfig(
                        backend_type="sql",
                        implementation_class="framework.persistence.backends.sql.SQLRepository",
                        config=backend_config,
                        enabled=True,
                        lazy_init=True  # SQL might need database setup
                    )
                )
        
        # Create persistence manager with registry
        async def create_persistence_manager():
            manager = PersistenceManager(registry)
            await manager.initialize()
            return manager
        
        self.container.register_singleton(
            "PersistenceManager",
            lambda: create_persistence_manager()
        )
        
        # Also register the registry itself for inspection
        self.container.register_singleton(
            "BackendRegistry", 
            lambda: registry
        )
    
    async def _configure_dispatcher(self):
        """Configure the event dispatcher"""
        def create_dispatcher(container: DIContainer):
            event_bus = container.get(EventBus)
            uow = container.get(UnitOfWork)
            return EventDispatcher(unit_of_work=uow, event_bus=event_bus)
        
        self.container.register_singleton(
            EventDispatcher,
            lambda: create_dispatcher(self.container)
        )
    
    async def _configure_unit_of_work(self):
        """Configure the Unit of Work"""
        def create_uow(container: DIContainer):
            event_bus = container.get(EventBus)
            persistence_manager = container.get("PersistenceManager")
            return UnitOfWork(event_bus=event_bus, persistence_manager=persistence_manager)
        
        self.container.register_singleton(
            UnitOfWork,
            lambda: create_uow(self.container)
        )
    
    async def _register_entities(self):
        """Register all entity classes with the container"""
        for entity_class in self._entities:
            # Register entity class itself
            self.container.register_singleton(
                f"Entity.{entity_class.__name__}",
                entity_class
            )
            
            # TODO: Set up entity-specific services (repositories, etc.)
    
    async def _configure_web_layer(self):
        """Configure web framework integration"""
        web_config = self.config.web
        
        if web_config.adapter == "FastHTMLAdapter":
            # This will be implemented once web layer is migrated
            pass

# Main configuration functions
async def configure_starmodel(
    app = None,
    entities: Optional[List[Type[Entity]]] = None,
    config: Optional[ApplicationConfig] = None
) -> DIContainer:
    """
    Configure StarModel with clean architecture.
    
    This is the main entry point for setting up a StarModel application
    with all clean architecture components properly wired.
    
    Args:
        app: Web application instance (FastHTML, FastAPI, etc.)
        entities: List of entity classes to register
        config: Application configuration
    
    Returns:
        Configured DI container
    """
    configurator = StarModelConfigurator(config)
    
    if entities:
        configurator.add_entities(entities)
    
    container = await configurator.configure()
    
    # If web app is provided, configure web integration
    if app is not None:
        await _configure_web_integration(app, container)
    
    return container

async def _configure_web_integration(app, container: DIContainer):
    """Configure web framework integration"""
    # This will be enhanced once web adapters are migrated
    # For now, provide basic integration
    
    dispatcher = container.get(EventDispatcher)
    
    # Store references in app for access by routes
    if hasattr(app, 'state'):
        app.state.starmodel_container = container
        app.state.starmodel_dispatcher = dispatcher
    else:
        # Fallback for frameworks without state
        app.starmodel_container = container
        app.starmodel_dispatcher = dispatcher

# Convenience functions for common scenarios
async def configure_development_app(entities: List[Type[Entity]]) -> DIContainer:
    """Quick setup for development environment"""
    from ...infrastructure.dependency_injection.configuration import Environment, ApplicationConfig
    
    config = ApplicationConfig.for_environment(Environment.DEVELOPMENT)
    return await configure_starmodel(entities=entities, config=config)

async def configure_production_app(entities: List[Type[Entity]], database_url: str) -> DIContainer:
    """Quick setup for production environment"""
    from ...infrastructure.dependency_injection.configuration import Environment, ApplicationConfig
    
    config = ApplicationConfig.for_environment(Environment.PRODUCTION)
    config.persistence.backends["sql"]["url"] = database_url
    
    return await configure_starmodel(entities=entities, config=config)

# Export main components
__all__ = [
    "StarModelConfigurator", "configure_starmodel",
    "configure_development_app", "configure_production_app"
]