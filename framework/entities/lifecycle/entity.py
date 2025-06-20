"""
Entity Lifecycle Management - The Heart of StarModel

This module contains the core Entity class that represents the fundamental
building block of StarModel applications. Entities are domain objects with
behavior, state, and event-driven interactions.

🎯 Entity-Centric Design:
- Entities contain both data AND behavior (@event methods)
- Automatic signal generation for reactive UI binding
- Pluggable persistence through configuration
- Real-time synchronization across clients
- Clean separation from infrastructure concerns
"""
from typing import Any, Optional, Dict, Type
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# Import from screaming architecture locations
try:
    from ...reactivity.signals.signal_system import SignalDescriptor
    from ...events.commands.event import EventMethodDescriptor
    from ..mixins import PersistenceMixin, SignalMixin, EventCapable, ValidationMixin
    # Note: datastar_script will be imported when web integration is needed
except ImportError:
    # Fallback to old imports during migration
    from starmodel.core.signals import SignalDescriptor
    from starmodel.core.events import EventMethodDescriptor
    from starmodel.core.mixins import EntityMixin as SignalMixin, PersistenceMixin
    
    # datastar_script will be available once web infrastructure is migrated
    
    # Placeholder for EventCapable during migration
    class EventCapable:
        pass
    
    # Placeholder for ValidationMixin during migration
    class ValidationMixin:
        pass

# Entity stores configuration
from enum import Enum

class EntityStore(Enum):
    """Available storage backends for entities"""
    SERVER_MEMORY = "server_memory"
    SERVER_SQL = "server_sql"
    SERVER_SQL_SQLITE = "server_sql_sqlite"
    SERVER_SQL_POSTGRESQL = "server_sql_postgresql"
    SERVER_SQL_MYSQL = "server_sql_mysql"
    SERVER_REDIS = "server_redis" 
    CLIENT_SESSION = "client_session"
    CLIENT_LOCAL = "client_local"
    CUSTOM = "custom"

class EntityConfig(ConfigDict):
    """
    Configuration for entity behavior and persistence.
    
    This configuration is declarative - entities specify WHAT they need,
    not HOW it's implemented. The framework handles the implementation.
    """
    
    # Storage configuration
    store: EntityStore = EntityStore.SERVER_MEMORY
    auto_persist: bool = True
    ttl: Optional[int] = None
    
    # SQL-specific configuration
    table_name: Optional[str] = None  # Custom table name (defaults to class name)
    schema: Optional[str] = None  # Database schema
    database_url: Optional[str] = None  # Custom database URL
    connection_pool_size: int = 10  # Connection pool configuration
    
    # Real-time configuration  
    realtime: bool = True
    sync_with_client: bool = True
    collaborative: bool = False
    
    # Signal configuration
    use_namespace: bool = False
    namespace: Optional[str] = None
    
    # Validation configuration
    validate_assignment: bool = True
    arbitrary_types_allowed: bool = True
    
    # JSON encoding
    json_encoders: Dict[Type, Any] = {datetime: lambda dt: dt.isoformat()}

class Entity(BaseModel, SignalMixin, PersistenceMixin, EventCapable, ValidationMixin):
    """
    Core Entity class - represents a domain object with behavior.
    
    Entities are the heart of StarModel applications. They:
    - Contain both data and behavior (@event methods)
    - Support reactive signals for UI binding  
    - Handle their own persistence through backends
    - Enable real-time collaboration
    - Maintain clean separation from infrastructure
    
    Example:
        class BlogPost(Entity):
            title: str
            content: str
            published: bool = False
            
            model_config = {
                "store": EntityStore.SERVER_SQL,
                "realtime": True,
                "collaborative": True
            }
            
            @event
            async def publish(self):
                self.published = True
                
            @event
            async def add_comment(self, comment: str, author: str):
                # Business logic here
                pass
    """
    
    # Default configuration - can be overridden in subclasses
    model_config = EntityConfig()
    
    # Core entity fields
    id: Optional[str] = Field(default=None, description="Unique identifier")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    def __init__(self, **data):
        """
        Initialize entity with automatic timestamping and persistence setup.
        
        During initialization:
        1. Set timestamps if not provided
        2. Generate ID if not provided
        3. Set up reactive signals
        4. Configure persistence backend
        5. Auto-save if configured
        """
        # Set timestamps
        if not data.get('created_at'):
            data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        
        # Initialize pydantic model
        super().__init__(**data)
        
        # Generate ID if not provided
        if not self.id:
            self.id = self._generate_id()
        
        # Auto-save if configured
        if self.get_config("auto_persist", True):
            self._auto_save()
    
    def __init_subclass__(cls, **kwargs):
        """
        Set up entity class when subclassed.
        
        This method:
        1. Creates signal descriptors for all fields
        2. Creates URL generator methods for @event methods
        3. Sets up namespace if configured
        4. Validates entity configuration
        """
        super().__init_subclass__(**kwargs)
        
        # Set up namespace
        if cls.get_config("use_namespace", False) and not cls.get_config("namespace"):
            cls.model_config["namespace"] = cls.__name__
        
        # Create signal descriptors for all model fields
        cls._setup_signals()
        
        # Create URL generator methods for @event decorated methods
        cls._setup_event_methods()
        
        # Validate entity configuration
        cls._validate_config()
    
    @classmethod
    def _setup_signals(cls):
        """Create signal descriptors for all entity fields"""
        # Regular fields
        for field_name in cls.model_fields:
            signal_name = f"{field_name}_signal"
            setattr(cls, signal_name, SignalDescriptor(field_name, cls))
        
        # Computed fields
        for field_name in cls.model_computed_fields:
            signal_name = f"{field_name}_signal"
            setattr(cls, signal_name, SignalDescriptor(field_name, cls))
    
    @classmethod
    def _setup_event_methods(cls):
        """Set up URL generator methods for @event decorated methods"""
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_event_metadata'):
                # Create URL generator method
                url_generator = EventMethodDescriptor(attr_name, cls.__name__, attr)
                setattr(cls, attr_name, url_generator)
    
    @classmethod
    def _validate_config(cls):
        """Validate entity configuration"""
        config = cls.model_config
        
        # Validate store type
        if isinstance(config.get("store"), str):
            try:
                config["store"] = EntityStore(config["store"])
            except ValueError:
                valid_stores = [store.value for store in EntityStore]
                raise ValueError(f"Invalid store '{config['store']}'. Valid options: {valid_stores}")
    
    @classmethod
    def get_config(cls, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback to default"""
        return getattr(cls.model_config, key, default)
    
    @classmethod  
    def get_store_config(cls) -> EntityStore:
        """Get configured storage type"""
        return cls.get_config("store", EntityStore.SERVER_MEMORY)
    
    @classmethod
    def get_persistence_manager(cls):
        """Request persistence manager from DI container"""
        # This will be implemented once DI container is migrated
        # For now, return a placeholder
        try:
            from ...infrastructure.dependency_injection import get_persistence_manager
            return get_persistence_manager()
        except ImportError:
            # Fallback during migration
            from starmodel.persistence.memory import MemoryRepo
            return MemoryRepo()
    
    def _generate_id(self) -> str:
        """Generate unique ID for entity"""
        import uuid
        return str(uuid.uuid4())
    
    def _auto_save(self):
        """Auto-save entity if configured"""
        try:
            # This will be async once persistence layer is migrated
            self.save()
        except Exception as e:
            # Don't fail initialization due to persistence issues
            print(f"Warning: Auto-save failed for {self.__class__.__name__}: {e}")
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now()
    
    async def save(self, **kwargs) -> str:
        """
        Save entity through appropriate persistence backend.
        
        Returns:
            str: The entity ID
        """
        self.update_timestamp()
        
        # Get persistence manager and save through it
        manager = self.get_persistence_manager()
        backend = manager.get_backend(self.__class__)
        self.id = await backend.save_entity(self, **kwargs)
        return self.id
    
    @classmethod
    async def get(cls, entity_id: str):
        """Load entity by ID through persistence manager"""
        manager = cls.get_persistence_manager()
        backend = manager.get_backend(cls)
        return await backend.load_entity(cls, entity_id)
    
    async def delete(self) -> bool:
        """Delete this entity through persistence manager"""
        if not self.id:
            return False
        
        manager = self.get_persistence_manager()
        backend = manager.get_backend(self.__class__)
        return await backend.delete_entity(self.__class__, self.id)
    
    @classmethod
    async def list_all(cls, limit: int = 100):
        """List all entities of this type"""
        manager = cls.get_persistence_manager()
        backend = manager.get_backend(cls)
        return await backend.list_entities(cls, limit)
    
    def get_signals(self) -> Dict[str, Any]:
        """Get current signal values for this entity"""
        signals = {}
        
        # Add field signals
        for field_name in self.__class__.model_fields:
            field_value = getattr(self, field_name)
            signal_key = self._get_signal_key(field_name)
            signals[signal_key] = field_value
        
        # Add computed field signals
        for field_name in getattr(self.__class__, 'model_computed_fields', {}):
            try:
                field_value = getattr(self, field_name)
                signal_key = self._get_signal_key(field_name)
                signals[signal_key] = field_value
            except Exception:
                # Computed field might not be available
                pass
        
        return signals
    
    def _get_signal_key(self, field_name: str) -> str:
        """Get the signal key for a field (with namespace if configured)"""
        if self.get_config("use_namespace", False):
            namespace = self.get_config("namespace", self.__class__.__name__)
            return f"{namespace}.{field_name}"
        return field_name
    
    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

# Backward compatibility alias
State = Entity

# Export for use in other modules
__all__ = ["Entity", "EntityStore", "EntityConfig", "State"]