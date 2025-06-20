"""
SQL Entity - FastSQLModel Integration for SQL Database Entities

🗃️ SQL Entity Support:
This module provides SQL-specific entity classes that integrate FastSQLModel
with the StarModel Entity system, enabling relational database persistence
while maintaining all StarModel functionality.

Key Features:
- Dual inheritance from Entity and BaseTable
- Automatic table configuration
- SQL field mapping with Pydantic validation
- Clean integration with repository pattern
- Transaction support through Unit of Work
"""

from typing import Any, Optional, Dict, Type, Union
from datetime import datetime
from uuid import uuid4

# Import FastSQLModel components
try:
    from fastsqlmodel import BaseTable, FastSQLModel
    from sqlalchemy import Column, String, DateTime, Boolean, Text
    from sqlalchemy.dialects.postgresql import UUID
    from sqlalchemy.sql import func
    SQL_AVAILABLE = True
except ImportError:
    # Graceful fallback when SQL dependencies are not available
    SQL_AVAILABLE = False
    BaseTable = object
    FastSQLModel = object
    Column = None
    String = None
    DateTime = None
    Boolean = None
    Text = None
    UUID = None
    func = None

from .entity import Entity, EntityStore, EntityConfig
from pydantic import Field

class SQLEntityConfig(EntityConfig):
    """Enhanced configuration for SQL entities"""
    
    # Override default store for SQL entities
    store: EntityStore = EntityStore.SERVER_SQL
    
    # SQL-specific settings
    table: bool = True  # Mark as database table
    include_relationships: bool = True  # Include SQLAlchemy relationships
    
    # Index configuration
    indexes: Optional[Dict[str, Any]] = None
    unique_constraints: Optional[Dict[str, Any]] = None
    
    # Migration settings
    migrate_from_memory: bool = False  # Auto-migrate from memory to SQL
    preserve_existing_data: bool = True

class SQLEntity(Entity):
    """
    Base class for SQL-backed entities.
    
    Provides a bridge between StarModel Entity and FastSQLModel BaseTable,
    enabling relational database persistence while maintaining all StarModel
    functionality including events, signals, and real-time updates.
    
    Usage:
        from fastsqlmodel import BaseTable
        
        class User(SQLEntity, BaseTable, table=True):
            __tablename__ = "users"
            
            username: str = Field(index=True)
            email: str = Field(unique=True)
            is_active: bool = True
            
            model_config = {
                "store": EntityStore.SERVER_SQL_POSTGRESQL,
                "database_url": "postgresql://user:pass@localhost/mydb"
            }
            
            @event
            async def activate(self):
                self.is_active = True
    """
    
    # Use SQL-specific configuration by default
    model_config = SQLEntityConfig()
    
    def __init_subclass__(cls, table: bool = False, **kwargs):
        """
        Set up SQL entity class when subclassed.
        
        This method handles the complex dual inheritance setup between
        StarModel Entity and FastSQLModel BaseTable.
        """
        # Ensure SQL is available
        if not SQL_AVAILABLE:
            raise ImportError(
                "SQL dependencies not available. "
                "Please install fastsqlmodel and sqlalchemy[asyncio] to use SQLEntity"
            )
        
        # Call parent init_subclass
        super().__init_subclass__(**kwargs)
        
        # Configure table if specified
        if table:
            cls._setup_sql_table()
        
        # Validate SQL configuration
        cls._validate_sql_config()
    
    @classmethod
    def _setup_sql_table(cls):
        """Set up SQL table configuration"""
        # Set default table name if not specified
        if not hasattr(cls, '__tablename__'):
            # Convert CamelCase to snake_case for table name
            table_name = cls.get_config("table_name")
            if not table_name:
                import re
                table_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', cls.__name__).lower()
            cls.__tablename__ = table_name
        
        # Set up default columns if not already defined
        cls._setup_default_columns()
    
    @classmethod
    def _setup_default_columns(cls):
        """Set up default SQL columns for StarModel fields"""
        # Only add columns if they don't already exist
        
        # ID column with UUID support
        if not hasattr(cls, 'id') or not hasattr(cls.id, 'type'):
            cls.id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
        
        # Timestamp columns
        if not hasattr(cls, 'created_at') or not hasattr(cls.created_at, 'type'):
            cls.created_at = Column(DateTime(timezone=True), server_default=func.now())
        
        if not hasattr(cls, 'updated_at') or not hasattr(cls.updated_at, 'type'):
            cls.updated_at = Column(
                DateTime(timezone=True), 
                server_default=func.now(),
                onupdate=func.now()
            )
    
    @classmethod
    def _validate_sql_config(cls):
        """Validate SQL-specific configuration"""
        config = cls.model_config
        
        # Ensure store is SQL-based
        store = config.get("store", EntityStore.SERVER_MEMORY)
        if not str(store.value).startswith("server_sql"):
            raise ValueError(
                f"SQLEntity {cls.__name__} must use a SQL store type, "
                f"got {store.value}"
            )
        
        # Validate database URL if provided
        database_url = config.get("database_url")
        if database_url and not isinstance(database_url, str):
            raise ValueError("database_url must be a string")
    
    @classmethod
    def get_table_name(cls) -> str:
        """Get the SQL table name for this entity"""
        return getattr(cls, '__tablename__', cls.__name__.lower())
    
    @classmethod
    def get_schema_name(cls) -> Optional[str]:
        """Get the SQL schema name for this entity"""
        return cls.get_config("schema")
    
    @classmethod
    def get_full_table_name(cls) -> str:
        """Get the full table name including schema"""
        schema = cls.get_schema_name()
        table = cls.get_table_name()
        return f"{schema}.{table}" if schema else table
    
    async def save(self, **kwargs) -> str:
        """
        Save SQL entity through repository.
        
        This method ensures that SQL entities are saved through the
        appropriate SQL repository while maintaining Entity interface.
        """
        self.update_timestamp()
        
        # Get SQL repository from persistence manager
        manager = self.get_persistence_manager()
        repository = await manager.get_repository(self.__class__)
        
        # Save through SQL repository
        self.id = await repository.save(self, **kwargs)
        return self.id
    
    @classmethod
    async def create_table(cls, engine=None):
        """Create the database table for this entity"""
        if not SQL_AVAILABLE:
            raise ImportError("SQL dependencies not available")
        
        if engine is None:
            # Get engine from persistence manager
            manager = cls.get_persistence_manager()
            repository = await manager.get_repository(cls)
            engine = repository.engine
        
        # Create table using FastSQLModel
        async with engine.begin() as conn:
            await conn.run_sync(cls.metadata.create_all)
    
    @classmethod
    async def drop_table(cls, engine=None):
        """Drop the database table for this entity"""
        if not SQL_AVAILABLE:
            raise ImportError("SQL dependencies not available")
        
        if engine is None:
            # Get engine from persistence manager
            manager = cls.get_persistence_manager()
            repository = await manager.get_repository(cls)
            engine = repository.engine
        
        # Drop table using FastSQLModel
        async with engine.begin() as conn:
            await conn.run_sync(cls.metadata.drop_all)

def create_sql_entity(
    name: str,
    fields: Dict[str, Any],
    table_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Type[SQLEntity]:
    """
    Dynamically create a SQL entity class.
    
    This function allows creating SQL entities programmatically,
    useful for migrations and dynamic schema generation.
    
    Args:
        name: Class name for the entity
        fields: Field definitions as {field_name: field_type}
        table_name: Optional custom table name
        config: Optional entity configuration
    
    Returns:
        Dynamically created SQL entity class
    """
    if not SQL_AVAILABLE:
        raise ImportError("SQL dependencies not available")
    
    # Create base attributes
    attrs = {}
    
    # Add table configuration
    if table_name:
        attrs['__tablename__'] = table_name
    
    # Add field definitions
    for field_name, field_def in fields.items():
        attrs[field_name] = field_def
    
    # Add configuration
    if config:
        entity_config = SQLEntityConfig(**config)
        attrs['model_config'] = entity_config
    
    # Create the class with dual inheritance
    return type(
        name,
        (SQLEntity, BaseTable),
        attrs,
        table=True
    )

# Migration utilities
async def migrate_entity_to_sql(
    entity_class: Type[Entity],
    sql_entity_class: Type[SQLEntity],
    batch_size: int = 100
):
    """
    Migrate entities from memory/other backend to SQL.
    
    This function provides a safe migration path from non-SQL
    backends to SQL databases.
    """
    if not SQL_AVAILABLE:
        raise ImportError("SQL dependencies not available")
    
    # Get persistence managers
    original_manager = entity_class.get_persistence_manager()
    sql_manager = sql_entity_class.get_persistence_manager()
    
    # Get repositories
    original_repo = await original_manager.get_repository(entity_class)
    sql_repo = await sql_manager.get_repository(sql_entity_class)
    
    # Ensure SQL table exists
    await sql_entity_class.create_table()
    
    # Stream entities in batches
    migrated_count = 0
    
    async for entity in original_repo.stream_all(entity_class, batch_size):
        # Convert to SQL entity
        entity_data = entity.model_dump()
        sql_entity = sql_entity_class(**entity_data)
        
        # Save to SQL
        await sql_entity.save()
        migrated_count += 1
    
    return migrated_count

# Helper for dual inheritance setup
class SQLEntityMeta(type):
    """Metaclass to help with dual inheritance setup"""
    
    def __new__(mcs, name, bases, attrs, **kwargs):
        # Handle table parameter
        table = kwargs.pop('table', False)
        
        # Create the class
        cls = super().__new__(mcs, name, bases, attrs)
        
        # Set up as table if specified
        if table and SQL_AVAILABLE:
            cls._setup_sql_table()
        
        return cls

# Export main components
__all__ = [
    "SQLEntity", "SQLEntityConfig", "create_sql_entity", 
    "migrate_entity_to_sql", "SQLEntityMeta"
]