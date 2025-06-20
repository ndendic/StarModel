"""
Session Management - Framework-Agnostic Session Handling

🔐 Clean Session Architecture:
This module provides session management capabilities that work across
different web frameworks while maintaining clean separation from
framework-specific session implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import uuid
from enum import Enum

class SessionStorage(Enum):
    """Session storage backends"""
    MEMORY = "memory"
    COOKIE = "cookie"
    DATABASE = "database"
    REDIS = "redis"
    FILE = "file"

@dataclass
class SessionConfig:
    """Session configuration"""
    storage: SessionStorage = SessionStorage.MEMORY
    secret_key: str = "starmodel-session-secret"
    session_lifetime: timedelta = field(default_factory=lambda: timedelta(hours=24))
    cookie_name: str = "starmodel_session"
    cookie_domain: Optional[str] = None
    cookie_path: str = "/"
    cookie_secure: bool = False
    cookie_http_only: bool = True
    cookie_same_site: str = "lax"
    auto_regenerate: bool = True
    cleanup_interval: int = 3600  # seconds

@dataclass
class SessionData:
    """Session data container"""
    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_authenticated: bool = False
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self):
        """Update last access time"""
        self.updated_at = datetime.now()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get session value"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set session value"""
        self.data[key] = value
        self.touch()
    
    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return session value"""
        value = self.data.pop(key, default)
        self.touch()
        return value
    
    def clear(self):
        """Clear all session data"""
        self.data.clear()
        self.touch()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "is_authenticated": self.is_authenticated
        }

class SessionStore(ABC):
    """Abstract session store interface"""
    
    @abstractmethod
    async def create_session(self, session_data: SessionData) -> str:
        """Create new session and return session ID"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID"""
        pass
    
    @abstractmethod
    async def update_session(self, session_data: SessionData) -> bool:
        """Update existing session"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete session by ID"""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired sessions and return count"""
        pass
    
    @abstractmethod
    async def get_active_sessions(self, user_id: Optional[str] = None) -> List[SessionData]:
        """Get active sessions, optionally filtered by user"""
        pass

class MemorySessionStore(SessionStore):
    """In-memory session store implementation"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
    
    async def create_session(self, session_data: SessionData) -> str:
        """Create new session in memory"""
        self.sessions[session_data.session_id] = session_data
        return session_data.session_id
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session from memory"""
        session = self.sessions.get(session_id)
        if session and session.is_expired():
            del self.sessions[session_id]
            return None
        return session
    
    async def update_session(self, session_data: SessionData) -> bool:
        """Update session in memory"""
        if session_data.session_id in self.sessions:
            self.sessions[session_data.session_id] = session_data
            return True
        return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from memory"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    async def cleanup_expired(self) -> int:
        """Clean up expired sessions from memory"""
        expired_ids = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired_ids:
            del self.sessions[session_id]
        
        return len(expired_ids)
    
    async def get_active_sessions(self, user_id: Optional[str] = None) -> List[SessionData]:
        """Get active sessions from memory"""
        active_sessions = []
        
        for session in self.sessions.values():
            if session.is_expired():
                continue
            
            if user_id is None or session.user_id == user_id:
                active_sessions.append(session)
        
        return active_sessions

class SessionManager:
    """
    Session manager for handling web sessions.
    
    Provides framework-agnostic session management with
    pluggable storage backends and comprehensive session lifecycle.
    """
    
    def __init__(self, config: SessionConfig, store: Optional[SessionStore] = None):
        self.config = config
        self.store = store or self._create_default_store()
        self._cleanup_task = None
    
    def _create_default_store(self) -> SessionStore:
        """Create default session store based on config"""
        if self.config.storage == SessionStorage.MEMORY:
            return MemorySessionStore()
        else:
            # For other storage types, default to memory for now
            # These would be implemented as separate classes
            return MemorySessionStore()
    
    async def create_session(self, 
                           user_id: Optional[str] = None,
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None) -> SessionData:
        """Create new session"""
        session_id = self._generate_session_id()
        expires_at = datetime.now() + self.config.session_lifetime
        
        session_data = SessionData(
            session_id=session_id,
            expires_at=expires_at,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self.store.create_session(session_data)
        return session_data
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID"""
        if not session_id:
            return None
        
        session = await self.store.get_session(session_id)
        if session and not session.is_expired():
            session.touch()
            await self.store.update_session(session)
            return session
        
        return None
    
    async def update_session(self, session_data: SessionData) -> bool:
        """Update session"""
        session_data.touch()
        return await self.store.update_session(session_data)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        return await self.store.delete_session(session_id)
    
    async def regenerate_session(self, old_session_id: str) -> Optional[SessionData]:
        """Regenerate session ID for security"""
        old_session = await self.get_session(old_session_id)
        if not old_session:
            return None
        
        # Create new session with same data
        new_session_id = self._generate_session_id()
        new_session = SessionData(
            session_id=new_session_id,
            data=old_session.data.copy(),
            user_id=old_session.user_id,
            ip_address=old_session.ip_address,
            user_agent=old_session.user_agent,
            is_authenticated=old_session.is_authenticated,
            expires_at=datetime.now() + self.config.session_lifetime
        )
        
        # Save new session and delete old one
        await self.store.create_session(new_session)
        await self.store.delete_session(old_session_id)
        
        return new_session
    
    async def authenticate_session(self, session_id: str, user_id: str) -> bool:
        """Mark session as authenticated"""
        session = await self.get_session(session_id)
        if session:
            session.user_id = user_id
            session.is_authenticated = True
            return await self.update_session(session)
        return False
    
    async def logout_session(self, session_id: str) -> bool:
        """Logout session (clear authentication)"""
        session = await self.get_session(session_id)
        if session:
            session.user_id = None
            session.is_authenticated = False
            return await self.update_session(session)
        return False
    
    async def cleanup_expired(self) -> int:
        """Clean up expired sessions"""
        return await self.store.cleanup_expired()
    
    def _generate_session_id(self) -> str:
        """Generate secure session ID"""
        return str(uuid.uuid4())
    
    # Session middleware integration
    async def process_request(self, request) -> Optional[SessionData]:
        """Process request to extract/create session"""
        # This would be implemented by web adapters
        # to extract session ID from cookies/headers
        pass
    
    async def process_response(self, response, session_data: SessionData):
        """Process response to set session cookies"""
        # This would be implemented by web adapters
        # to set session cookies in response
        pass

class SessionMiddleware:
    """
    Session middleware for automatic session handling.
    
    Automatically handles session creation, retrieval, and cleanup
    for web requests.
    """
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
    
    async def __call__(self, request, call_next):
        """Process request with session handling"""
        # Extract session ID from request
        session_id = self._extract_session_id(request)
        
        # Get or create session
        session_data = None
        if session_id:
            session_data = await self.session_manager.get_session(session_id)
        
        if not session_data:
            session_data = await self.session_manager.create_session(
                ip_address=getattr(request, 'client_ip', None),
                user_agent=getattr(request, 'user_agent', None)
            )
        
        # Add session to request
        request.session = session_data
        
        # Process request
        response = await call_next(request)
        
        # Update session
        await self.session_manager.update_session(session_data)
        
        # Set session cookie in response
        self._set_session_cookie(response, session_data)
        
        return response
    
    def _extract_session_id(self, request) -> Optional[str]:
        """Extract session ID from request"""
        # This would be implemented by specific adapters
        # to extract from cookies/headers
        return None
    
    def _set_session_cookie(self, response, session_data: SessionData):
        """Set session cookie in response"""
        # This would be implemented by specific adapters
        # to set cookies in response
        pass

# Export main components
__all__ = [
    "SessionManager", "SessionData", "SessionConfig", "SessionStorage",
    "SessionStore", "MemorySessionStore", "SessionMiddleware"
]