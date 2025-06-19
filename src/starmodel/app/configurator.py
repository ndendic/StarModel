"""
Application Configurator

Centralized application configuration for StarModel applications.
Handles initialization order and provides a clean API for app setup.
"""

from typing import List, Type, Optional, Union
from fasthtml.common import FastHTML
from sqlmodel import SQLModel

from ..core.entity import Entity
from ..core.entity_sql import SQLEntity
from ..persistence import SQLModelBackend, get_memory_persistence, start_all_cleanup
from ..adapters.fasthtml import register_entities, register_all_entities, include_entity
from ..app.dispatcher import call_event
from ..app.uow import UnitOfWork
from ..app.bus import InProcessBus


def configure_app(
    app: FastHTML,
    entities: Union[List[Type[Entity]], str, None] = None,
    initialize_db: bool = True,
    start_cleanup: bool = True,
    **config
) -> None:
    """
    Configure StarModel application with proper initialization order.
    
    This function should be called AFTER all entity classes are imported
    but BEFORE starting the application server.
    
    Args:
        app: FastHTML application instance
        entities: Entity classes to register, or 'auto' for auto-discovery, or None for all subclasses
        initialize_db: Whether to initialize database tables
        start_cleanup: Whether to start automatic cleanup tasks
        **config: Additional configuration options
        
    Example:
        ```python
        from fasthtml import FastHTML
        from starmodel import configure_app
        from app.entities import CounterEntity, ProductEntity
        
        app = FastHTML()
        
        # Option 1: Explicit entity list
        configure_app(app, entities=[CounterEntity, ProductEntity])
        
        # Option 2: Auto-discovery 
        configure_app(app, entities='auto')
        
        # Option 3: Register all Entity subclasses (default)
        configure_app(app)
        
        app.run()
        ```
    """
    print("🚀 Configuring StarModel application...")
    
    # Step 1: Initialize database tables (AFTER all models are defined)
    if initialize_db:
        _initialize_database_tables()
    
    # Step 2: Set up Unit of Work and dependencies
    bus = InProcessBus()
    uow = UnitOfWork(bus)
    
    # Step 3: Register entity routes based on the entities parameter
    if entities == 'auto':
        print("📡 Auto-registering all entities...")
        register_all_entities(app.route)
    elif entities is None:
        print("📡 Registering all Entity subclasses...")
        _register_all_entity_subclasses(app.route, uow)
    elif isinstance(entities, list):
        print(f"📡 Registering {len(entities)} specified entities...")
        register_entities(app.route, entities, uow)
    else:
        raise ValueError("entities must be a list, 'auto', or None")
    
    # Step 4: Start cleanup tasks
    if start_cleanup:
        _start_cleanup_tasks()
    
    print("✅ StarModel application configured successfully!")


def _initialize_database_tables() -> None:
    """Initialize database tables for all SQL entities."""
    print("🗃️  Initializing database tables...")
    
    try:
        # Get the SQL backend (singleton)
        sql_backend = SQLModelBackend()
        
        # Create all tables for defined models
        # This must happen AFTER all SQLEntity models are imported
        SQLModel.metadata.create_all(sql_backend.engine)
        
        print(f"✅ Database tables initialized: {sql_backend.engine.url}")
        
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        raise


def _register_all_entity_subclasses(router, uow: UnitOfWork) -> None:
    """Register all Entity subclasses (both Entity and SQLEntity)."""
    all_entities = []
    
    # Find all Entity subclasses
    for entity_class in Entity.__subclasses__():
        all_entities.append(entity_class)
        print(f"  📝 Found Entity: {entity_class.__name__}")
    
    # Find all SQLEntity subclasses  
    if hasattr(SQLEntity, '__subclasses__'):
        for entity_class in SQLEntity.__subclasses__():
            all_entities.append(entity_class)
            print(f"  📝 Found SQLEntity: {entity_class.__name__}")
    
    if all_entities:
        register_entities(router, all_entities, uow)
        print(f"✅ Registered {len(all_entities)} entity classes")
    else:
        print("⚠️  No entity classes found to register")


def _start_cleanup_tasks() -> None:
    """Start automatic cleanup tasks for all persistence backends."""
    print("🧹 Starting cleanup tasks...")
    
    try:
        start_all_cleanup()
        print("✅ Cleanup tasks started")
    except Exception as e:
        print(f"⚠️  Failed to start cleanup tasks: {e}")


def validate_app_configuration() -> dict:
    """
    Validate that the application is properly configured.
    
    Returns:
        Dictionary with validation results
    """
    results = {
        'entities_found': 0,
        'sql_entities_found': 0,
        'database_initialized': False,
        'errors': []
    }
    
    try:
        # Count entities
        results['entities_found'] = len(Entity.__subclasses__())
        if hasattr(SQLEntity, '__subclasses__'):
            results['sql_entities_found'] = len(SQLEntity.__subclasses__())
        
        # Check database
        try:
            sql_backend = SQLModelBackend()
            results['database_initialized'] = sql_backend.engine is not None
        except Exception as e:
            results['errors'].append(f"Database check failed: {e}")
            
    except Exception as e:
        results['errors'].append(f"Validation failed: {e}")
    
    return results