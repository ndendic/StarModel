"""
FastState Persistence Layer

This module provides optional state persistence with Redis and database backends
for production use. States can be automatically persisted and loaded based on
configuration.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, Union
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

try:
    from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = None


class StatePersistenceBackend(ABC):
    """
    Abstract base class for state persistence backends.
    
    Implementations must provide methods for saving, loading, and managing
    state data with optional TTL support.
    """
    
    @abstractmethod
    async def save_state(self, key: str, state_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Save state data to the persistence backend.
        
        Args:
            key: Unique identifier for the state
            state_data: State data to persist (JSON-serializable)
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Load state data from the persistence backend.
        
        Args:
            key: Unique identifier for the state
            
        Returns:
            State data dictionary if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete_state(self, key: str) -> bool:
        """
        Delete state data from the persistence backend.
        
        Args:
            key: Unique identifier for the state
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if state exists in the persistence backend.
        
        Args:
            key: Unique identifier for the state
            
        Returns:
            True if state exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Clean up expired state entries.
        
        Returns:
            Number of entries cleaned up
        """
        pass


class RedisStatePersistence(StatePersistenceBackend):
    """
    Redis-based state persistence implementation.
    
    Provides fast, in-memory persistence with automatic TTL support.
    Ideal for session-scoped and short-lived state data.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "faststate:"):
        """
        Initialize Redis persistence backend.
        
        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for state data
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not available. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.prefix = prefix
        self._redis = None
        
    @property
    def redis(self):
        """Get Redis connection, creating it if necessary."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.prefix}{key}"
    
    async def save_state(self, key: str, state_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Save state to Redis with optional TTL."""
        try:
            redis_key = self._make_key(key)
            serialized_data = json.dumps(state_data)
            
            if ttl:
                result = self.redis.setex(redis_key, ttl, serialized_data)
            else:
                result = self.redis.set(redis_key, serialized_data)
            
            return bool(result)
            
        except Exception as e:
            print(f"Error saving state to Redis: {e}")
            return False
    
    async def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Load state from Redis."""
        try:
            redis_key = self._make_key(key)
            serialized_data = self.redis.get(redis_key)
            
            if serialized_data:
                return json.loads(serialized_data)
            return None
            
        except Exception as e:
            print(f"Error loading state from Redis: {e}")
            return None
    
    async def delete_state(self, key: str) -> bool:
        """Delete state from Redis."""
        try:
            redis_key = self._make_key(key)
            result = self.redis.delete(redis_key)
            return result > 0
            
        except Exception as e:
            print(f"Error deleting state from Redis: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if state exists in Redis."""
        try:
            redis_key = self._make_key(key)
            return bool(self.redis.exists(redis_key))
            
        except Exception as e:
            print(f"Error checking state existence in Redis: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """Redis handles TTL automatically, so no cleanup needed."""
        return 0


class DatabaseStatePersistence(StatePersistenceBackend):
    """
    Database-based state persistence implementation.
    
    Provides durable persistence for long-lived state data.
    Ideal for user-scoped and global state data.
    """
    
    def __init__(self, database_url: str = "sqlite:///faststate.db", table_name: str = "faststate_data"):
        """
        Initialize database persistence backend.
        
        Args:
            database_url: SQLAlchemy database URL
            table_name: Table name for state data
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy is not available. Install with: pip install sqlalchemy")
        
        self.database_url = database_url
        self.table_name = table_name
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create state data model
        self._create_state_model()
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    def _create_state_model(self):
        """Create SQLAlchemy model for state data."""
        # Check if model already exists
        if hasattr(self, 'StateData'):
            return
            
        class StateData(Base):
            __tablename__ = self.table_name
            __table_args__ = {'extend_existing': True}
            
            key = Column(String(255), primary_key=True)
            data = Column(Text, nullable=False)
            created_at = Column(DateTime, default=datetime.utcnow)
            updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
            expires_at = Column(DateTime, nullable=True)
        
        self.StateData = StateData
    
    def _get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    async def save_state(self, key: str, state_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Save state to database with optional TTL."""
        try:
            session = self._get_session()
            
            try:
                # Calculate expiration time
                expires_at = None
                if ttl:
                    expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                
                # Check if state already exists
                existing = session.query(self.StateData).filter_by(key=key).first()
                
                if existing:
                    # Update existing state
                    existing.data = json.dumps(state_data)
                    existing.updated_at = datetime.utcnow()
                    existing.expires_at = expires_at
                else:
                    # Create new state
                    new_state = self.StateData(
                        key=key,
                        data=json.dumps(state_data),
                        expires_at=expires_at
                    )
                    session.add(new_state)
                
                session.commit()
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            print(f"Error saving state to database: {e}")
            return False
    
    async def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Load state from database."""
        try:
            session = self._get_session()
            
            try:
                state_entry = session.query(self.StateData).filter_by(key=key).first()
                
                if not state_entry:
                    return None
                
                # Check if expired
                if state_entry.expires_at and state_entry.expires_at < datetime.utcnow():
                    # Delete expired entry
                    session.delete(state_entry)
                    session.commit()
                    return None
                
                return json.loads(state_entry.data)
                
            finally:
                session.close()
                
        except Exception as e:
            print(f"Error loading state from database: {e}")
            return None
    
    async def delete_state(self, key: str) -> bool:
        """Delete state from database."""
        try:
            session = self._get_session()
            
            try:
                result = session.query(self.StateData).filter_by(key=key).delete()
                session.commit()
                return result > 0
                
            finally:
                session.close()
                
        except Exception as e:
            print(f"Error deleting state from database: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if state exists in database."""
        try:
            session = self._get_session()
            
            try:
                count = session.query(self.StateData).filter_by(key=key).count()
                return count > 0
                
            finally:
                session.close()
                
        except Exception as e:
            print(f"Error checking state existence in database: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """Clean up expired state entries from database."""
        try:
            session = self._get_session()
            
            try:
                result = session.query(self.StateData).filter(
                    self.StateData.expires_at < datetime.utcnow()
                ).delete()
                session.commit()
                return result
                
            finally:
                session.close()
                
        except Exception as e:
            print(f"Error cleaning up expired states: {e}")
            return 0


class MemoryStatePersistence(StatePersistenceBackend):
    """
    In-memory state persistence implementation.
    
    Provides fast persistence for development and testing.
    Data is lost when the application restarts.
    """
    
    def __init__(self):
        """Initialize memory persistence backend."""
        self._data: Dict[str, Dict[str, Any]] = {}
        self._expiry: Dict[str, float] = {}
    
    async def save_state(self, key: str, state_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Save state to memory with optional TTL."""
        try:
            self._data[key] = state_data.copy()
            
            if ttl:
                self._expiry[key] = time.time() + ttl
            elif key in self._expiry:
                del self._expiry[key]
            
            return True
            
        except Exception as e:
            print(f"Error saving state to memory: {e}")
            return False
    
    async def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Load state from memory."""
        try:
            # Check if expired
            if key in self._expiry and time.time() > self._expiry[key]:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return None
            
            return self._data.get(key)
            
        except Exception as e:
            print(f"Error loading state from memory: {e}")
            return None
    
    async def delete_state(self, key: str) -> bool:
        """Delete state from memory."""
        try:
            existed = key in self._data
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return existed
            
        except Exception as e:
            print(f"Error deleting state from memory: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if state exists in memory."""
        try:
            # Check if expired
            if key in self._expiry and time.time() > self._expiry[key]:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return False
            
            return key in self._data
            
        except Exception as e:
            print(f"Error checking state existence in memory: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """Clean up expired state entries from memory."""
        try:
            current_time = time.time()
            expired_keys = [
                key for key, expiry_time in self._expiry.items()
                if current_time > expiry_time
            ]
            
            for key in expired_keys:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
            
            return len(expired_keys)
            
        except Exception as e:
            print(f"Error cleaning up expired states: {e}")
            return 0


class StatePersistenceManager:
    """
    Manager for state persistence operations.
    
    Coordinates between different persistence backends and provides
    a unified interface for saving and loading state data.
    """
    
    def __init__(self, default_backend: Optional[StatePersistenceBackend] = None):
        """
        Initialize persistence manager.
        
        Args:
            default_backend: Default persistence backend to use
        """
        self.default_backend = default_backend or MemoryStatePersistence()
        self.backends: Dict[str, StatePersistenceBackend] = {
            "default": self.default_backend
        }
    
    def add_backend(self, name: str, backend: StatePersistenceBackend):
        """Add a named persistence backend."""
        self.backends[name] = backend
    
    def get_backend(self, name: str = "default") -> StatePersistenceBackend:
        """Get a persistence backend by name."""
        return self.backends.get(name, self.default_backend)
    
    async def save_state(
        self,
        key: str,
        state_data: Dict[str, Any],
        ttl: Optional[int] = None,
        backend: str = "default"
    ) -> bool:
        """Save state using specified backend."""
        persistence_backend = self.get_backend(backend)
        return await persistence_backend.save_state(key, state_data, ttl)
    
    async def load_state(self, key: str, backend: str = "default") -> Optional[Dict[str, Any]]:
        """Load state using specified backend."""
        persistence_backend = self.get_backend(backend)
        return await persistence_backend.load_state(key)
    
    async def delete_state(self, key: str, backend: str = "default") -> bool:
        """Delete state using specified backend."""
        persistence_backend = self.get_backend(backend)
        return await persistence_backend.delete_state(key)
    
    async def exists(self, key: str, backend: str = "default") -> bool:
        """Check if state exists using specified backend."""
        persistence_backend = self.get_backend(backend)
        return await persistence_backend.exists(key)
    
    async def cleanup_expired(self, backend: str = "default") -> int:
        """Clean up expired states using specified backend."""
        persistence_backend = self.get_backend(backend)
        return await persistence_backend.cleanup_expired()


# Global persistence manager instance
persistence_manager = StatePersistenceManager()