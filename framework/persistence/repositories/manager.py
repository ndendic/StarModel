"""
Persistence Manager - Backend Factory and Coordination

🏭 Backend Factory and Service Coordination:
This module provides the central persistence manager that acts as a factory
for different persistence backends and coordinates their lifecycle and configuration.
"""

from typing import Dict, Type, Optional, Any, List, Union
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
import logging
from dataclasses import dataclass, field

# Import components
from .interface import EntityRepository, TransactionContext
from ...entities.configuration.store import EntityStore

# Forward reference to Entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...entities.lifecycle.entity import Entity

logger = logging.getLogger(__name__)

@dataclass
class BackendConfig:
    """Configuration for a persistence backend"""
    backend_type: str
    implementation_class: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    lazy_init: bool = True
    health_check_interval: int = 60  # seconds
    max_retry_attempts: int = 3

class BackendRegistry:
    """
    Registry for persistence backend implementations.
    
    Manages the mapping between EntityStore enums and concrete
    repository implementations, enabling pluggable persistence.
    """
    
    def __init__(self):
        self._backends: Dict[EntityStore, BackendConfig] = {}
        self._default_backends = self._get_default_backends()
    
    def register_backend(self, store_type: EntityStore, config: BackendConfig):
        """Register a persistence backend"""
        self._backends[store_type] = config
        logger.info(f"Registered backend for {store_type}: {config.implementation_class}")
    
    def get_backend_config(self, store_type: EntityStore) -> Optional[BackendConfig]:
        """Get backend configuration for a store type"""
        return self._backends.get(store_type) or self._default_backends.get(store_type)
    
    def list_backends(self) -> Dict[EntityStore, BackendConfig]:
        """List all registered backends"""
        return {**self._default_backends, **self._backends}
    
    def _get_default_backends(self) -> Dict[EntityStore, BackendConfig]:
        """Get default backend configurations"""
        return {
            EntityStore.SERVER_MEMORY: BackendConfig(
                backend_type="memory",
                implementation_class="framework.persistence.backends.memory.MemoryRepository",
                config={
                    "cleanup_interval": 300,
                    "max_entities": 10000,
                    "ttl_default": 3600
                }
            ),
            EntityStore.SERVER_SQL: BackendConfig(
                backend_type="sql",
                implementation_class="framework.persistence.repositories.sql.SQLRepository",
                config={
                    "database_url": "sqlite+aiosqlite:///starmodel.db",
                    "pool_size": 10,
                    "echo": False
                }
            ),
            EntityStore.SERVER_SQL_SQLITE: BackendConfig(
                backend_type="sql_sqlite",
                implementation_class="framework.persistence.repositories.sql.SQLRepository",
                config={
                    "database_url": "sqlite+aiosqlite:///starmodel.db",
                    "pool_size": 5,
                    "echo": False
                }
            ),
            EntityStore.SERVER_SQL_POSTGRESQL: BackendConfig(
                backend_type="sql_postgresql",
                implementation_class="framework.persistence.repositories.sql.SQLRepository",
                config={
                    "database_url": "postgresql+asyncpg://postgres:password@localhost:5432/starmodel",
                    "pool_size": 10,
                    "echo": False
                }
            ),
            EntityStore.SERVER_SQL_MYSQL: BackendConfig(
                backend_type="sql_mysql",
                implementation_class="framework.persistence.repositories.sql.SQLRepository",
                config={
                    "database_url": "mysql+aiomysql://root:password@localhost:3306/starmodel",
                    "pool_size": 10,
                    "echo": False
                }
            ),
            EntityStore.CLIENT_SESSION: BackendConfig(
                backend_type="client_session",
                implementation_class="framework.persistence.backends.client.SessionRepository",
                config={
                    "storage_type": "sessionStorage"
                }
            ),
            EntityStore.CLIENT_LOCAL: BackendConfig(
                backend_type="client_local", 
                implementation_class="framework.persistence.backends.client.LocalRepository",
                config={
                    "storage_type": "localStorage"
                }
            )
        }

class PersistenceError(Exception):
    """Base exception for persistence operations"""
    pass

class BackendNotFoundError(PersistenceError):
    """Raised when a backend is not found"""
    pass

class BackendInitializationError(PersistenceError):
    """Raised when backend initialization fails"""
    pass

class PersistenceManager:
    """
    Central persistence manager that coordinates all persistence backends.
    
    This manager acts as a factory for repositories and provides:
    - Backend lifecycle management
    - Configuration-driven backend selection
    - Health monitoring and diagnostics
    - Transaction coordination across backends
    """
    
    def __init__(self, registry: Optional[BackendRegistry] = None):
        self.registry = registry or BackendRegistry()
        self._repositories: Dict[EntityStore, EntityRepository] = {}
        self._backend_instances: Dict[str, Any] = {}
        self._health_tasks: Dict[str, asyncio.Task] = {}
        self._is_initialized = False
    
    async def initialize(self):
        """Initialize the persistence manager"""
        if self._is_initialized:
            return
        
        logger.info("Initializing PersistenceManager")
        
        # Initialize enabled backends
        for store_type, config in self.registry.list_backends().items():
            if config.enabled and not config.lazy_init:
                await self._initialize_backend(store_type, config)
        
        self._is_initialized = True
        logger.info("PersistenceManager initialized successfully")
    
    async def shutdown(self):
        """Shutdown the persistence manager and all backends"""
        logger.info("Shutting down PersistenceManager")
        
        # Cancel health check tasks
        for task in self._health_tasks.values():
            task.cancel()
        
        # Shutdown all backend instances
        for backend in self._backend_instances.values():
            if hasattr(backend, 'shutdown'):
                try:
                    await backend.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down backend: {e}")
        
        self._repositories.clear()
        self._backend_instances.clear()
        self._health_tasks.clear()
        self._is_initialized = False
        
        logger.info("PersistenceManager shutdown complete")
    
    async def get_repository(self, entity_class: Type['Entity']) -> EntityRepository:
        """
        Get repository for an entity class.
        
        Args:
            entity_class: The entity class
            
        Returns:
            Repository instance for the entity
            
        Raises:
            BackendNotFoundError: If no backend is configured for the entity
            BackendInitializationError: If backend initialization fails
        """
        # Determine the store type for this entity
        store_type = self._get_entity_store_type(entity_class)
        
        # Check if repository already exists
        if store_type in self._repositories:
            return self._repositories[store_type]
        
        # Get backend configuration
        config = self.registry.get_backend_config(store_type)
        if not config:
            raise BackendNotFoundError(f"No backend configured for store type: {store_type}")
        
        # Initialize backend if needed
        if store_type not in self._repositories:
            await self._initialize_backend(store_type, config)
        
        return self._repositories[store_type]
    
    async def get_repository_for_store(self, store_type: EntityStore) -> EntityRepository:
        """
        Get repository for a specific store type.
        
        Args:
            store_type: The entity store type
            
        Returns:
            Repository instance
        """
        if store_type in self._repositories:
            return self._repositories[store_type]
        
        config = self.registry.get_backend_config(store_type)
        if not config:
            raise BackendNotFoundError(f"No backend configured for store type: {store_type}")
        
        await self._initialize_backend(store_type, config)
        return self._repositories[store_type]
    
    def _get_entity_store_type(self, entity_class: Type['Entity']) -> EntityStore:
        """Extract store type from entity configuration"""
        # Check entity's model_config for store setting
        if hasattr(entity_class, 'model_config') and isinstance(entity_class.model_config, dict):
            store = entity_class.model_config.get('store')
            if isinstance(store, EntityStore):
                return store
        
        # Check for get_store_config method
        if hasattr(entity_class, 'get_store_config'):
            return entity_class.get_store_config()
        
        # Default to server memory
        return EntityStore.SERVER_MEMORY
    
    async def _initialize_backend(self, store_type: EntityStore, config: BackendConfig):
        """Initialize a backend instance"""
        if store_type in self._repositories:
            return
        
        logger.info(f"Initializing backend for {store_type}: {config.implementation_class}")
        
        try:
            # Create backend instance
            backend_class = self._load_backend_class(config.implementation_class)
            backend_instance = backend_class(**config.config)
            
            # Initialize if needed
            if hasattr(backend_instance, 'initialize'):
                await backend_instance.initialize()
            
            # Store instances
            self._repositories[store_type] = backend_instance
            self._backend_instances[config.backend_type] = backend_instance
            
            # Start health monitoring if configured
            if config.health_check_interval > 0:
                self._start_health_monitoring(store_type, config)
            
            logger.info(f"Backend {store_type} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize backend {store_type}: {e}")
            raise BackendInitializationError(f"Backend initialization failed: {e}")
    
    def _load_backend_class(self, class_path: str) -> Type[EntityRepository]:
        """Load backend class from module path"""
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            
            # Handle relative imports from framework
            if module_path.startswith('framework.'):
                # Import from current package structure
                from importlib import import_module
                module = import_module(f"...{module_path[10:]}", __name__)
            else:
                # Import from absolute path
                from importlib import import_module
                module = import_module(module_path)
            
            return getattr(module, class_name)
            
        except (ImportError, AttributeError) as e:
            # Fallback to built-in backends
            return self._get_builtin_backend(class_path)
    
    def _get_builtin_backend(self, class_path: str) -> Type[EntityRepository]:
        """Get built-in backend implementation"""
        builtin_backends = {
            "framework.persistence.backends.memory.MemoryRepository": "MemoryRepository",
            "framework.persistence.repositories.sql.SQLRepository": "SQLRepository",
            "framework.persistence.backends.client.SessionRepository": "ClientRepository", 
            "framework.persistence.backends.client.LocalRepository": "ClientRepository"
        }
        
        backend_name = builtin_backends.get(class_path)
        if not backend_name:
            raise ImportError(f"Backend not found: {class_path}")
        
        # Import actual implementations
        if backend_name == "MemoryRepository":
            from ..backends.memory import MemoryRepository
            return MemoryRepository
        elif backend_name == "SQLRepository":
            from .sql import SQLRepository
            return SQLRepository
        else:
            # For client repositories, return placeholder for now
            from .base import BaseRepository
            return BaseRepository
    
    def _start_health_monitoring(self, store_type: EntityStore, config: BackendConfig):
        """Start health monitoring for a backend"""
        async def health_check():
            while True:
                try:
                    await asyncio.sleep(config.health_check_interval)
                    repository = self._repositories.get(store_type)
                    
                    if repository and hasattr(repository, 'get_metrics'):
                        metrics = await repository.get_metrics()
                        logger.debug(f"Backend {store_type} health: {metrics}")
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Health check failed for {store_type}: {e}")
        
        task = asyncio.create_task(health_check())
        self._health_tasks[f"{store_type}"] = task
    
    # Transaction coordination methods
    async def begin_transaction(self, store_types: List[EntityStore]) -> Dict[EntityStore, TransactionContext]:
        """Begin transactions across multiple backends"""
        contexts = {}
        
        for store_type in store_types:
            repository = await self.get_repository_for_store(store_type)
            context = await repository.begin_transaction()
            contexts[store_type] = context
        
        return contexts
    
    async def commit_transactions(self, contexts: Dict[EntityStore, TransactionContext]):
        """Commit transactions across multiple backends"""
        for store_type, context in contexts.items():
            repository = self._repositories[store_type]
            await repository.commit_transaction(context)
    
    async def rollback_transactions(self, contexts: Dict[EntityStore, TransactionContext]):
        """Rollback transactions across multiple backends"""
        for store_type, context in contexts.items():
            repository = self._repositories[store_type]
            await repository.rollback_transaction(context)
    
    # Diagnostics and monitoring
    async def get_backend_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all backends"""
        status = {}
        
        for store_type, repository in self._repositories.items():
            try:
                metrics = await repository.get_metrics()
                status[store_type.value] = {
                    "status": "healthy",
                    "metrics": metrics,
                    "last_check": datetime.now().isoformat()
                }
            except Exception as e:
                status[store_type.value] = {
                    "status": "unhealthy", 
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
        
        return status
    
    async def cleanup_all_backends(self) -> Dict[str, int]:
        """Run cleanup on all backends"""
        results = {}
        cutoff_time = datetime.now()
        
        for store_type, repository in self._repositories.items():
            try:
                # This is a simplified cleanup - real implementation would vary by backend
                if hasattr(repository, 'cleanup_expired'):
                    from ...entities.lifecycle.entity import Entity
                    cleaned = await repository.cleanup_expired(Entity, cutoff_time)
                    results[store_type.value] = cleaned
                else:
                    results[store_type.value] = 0
            except Exception as e:
                logger.error(f"Cleanup failed for {store_type}: {e}")
                results[store_type.value] = -1
        
        return results

# Convenience functions
async def create_persistence_manager(
    registry: Optional[BackendRegistry] = None,
    auto_initialize: bool = True
) -> PersistenceManager:
    """Create and optionally initialize a persistence manager"""
    manager = PersistenceManager(registry)
    
    if auto_initialize:
        await manager.initialize()
    
    return manager

def create_backend_registry() -> BackendRegistry:
    """Create a new backend registry with default backends"""
    return BackendRegistry()

# Export main components
__all__ = [
    "PersistenceManager", "BackendRegistry", "BackendConfig",
    "PersistenceError", "BackendNotFoundError", "BackendInitializationError",
    "create_persistence_manager", "create_backend_registry"
]