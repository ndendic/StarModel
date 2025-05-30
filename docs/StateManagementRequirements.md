# FastState Advanced State Management Requirements

## Overview

The current FastState implementation has several limitations that prevent it from being production-ready:

1. **Simplistic State Registry**: All states stored in a global `_STATE_REGISTRY` without proper scoping
2. **Manual State Retrieval**: Requiring `state = _get_state(request, MyState)` in every route
3. **No Authentication/Authorization**: Events are publicly accessible without security controls
4. **SSE Connection Issues**: Multiple tabs create separate state instances instead of sharing session state
5. **Limited State Types**: Only supports session-based states, no global or record-based states

## Requirement 1: Advanced State ID Management and Scoping

### Current Problem
```python
# Current approach - too simplistic
_STATE_REGISTRY: dict[str, ReactiveState] = {}
sid_key = f"{cls.__name__}_id"  # Only class name, no scoping
```

### Solution: Hierarchical State Scoping

#### 1.1 State Scope Types
```python
from enum import Enum

class StateScope(Enum):
    GLOBAL = "global"        # Shared across all users (e.g., system settings)
    SESSION = "session"      # Per user session (current behavior)
    USER = "user"           # Per authenticated user (persists across sessions)
    COMPONENT = "component"  # Per component instance (multiple per page)
    RECORD = "record"       # Tied to a specific database record
    TEMPORARY = "temporary"  # Short-lived, auto-cleanup
```

#### 1.2 State ID Generation Strategy
```python
class StateIdentifier:
    def __init__(self, scope: StateScope, cls_name: str, **kwargs):
        self.scope = scope
        self.cls_name = cls_name
        self.user_id = kwargs.get('user_id')
        self.session_id = kwargs.get('session_id') 
        self.component_id = kwargs.get('component_id')
        self.record_id = kwargs.get('record_id')
        
    def generate_key(self) -> str:
        """Generate hierarchical state key"""
        parts = [self.scope.value, self.cls_name]
        
        if self.scope == StateScope.GLOBAL:
            # global:MyState
            pass
        elif self.scope == StateScope.SESSION:
            # session:abc123:MyState
            parts.append(self.session_id)
        elif self.scope == StateScope.USER:
            # user:user456:MyState
            parts.append(f"user{self.user_id}")
        elif self.scope == StateScope.COMPONENT:
            # session:abc123:component:comp789:MyState
            parts.extend([self.session_id, "component", self.component_id])
        elif self.scope == StateScope.RECORD:
            # record:MyState:123 (for MyState with record ID 123)
            parts.append(str(self.record_id))
            
        return ":".join(parts)
```

#### 1.3 Enhanced State Registry
```python
class StateRegistry:
    def __init__(self):
        self._states: dict[str, ReactiveState] = {}
        self._connections: dict[str, set[SSEConnection]] = {}  # Track SSE connections per state
        self._cleanup_tasks: dict[str, asyncio.Task] = {}
        
    def get_state(self, identifier: StateIdentifier, cls: type[ReactiveState], **kwargs) -> ReactiveState:
        key = identifier.generate_key()
        
        if key not in self._states:
            # Create new state based on scope
            if identifier.scope == StateScope.RECORD and identifier.record_id:
                # Load from database
                state = self._load_from_db(cls, identifier.record_id)
            else:
                # Create new instance
                state = cls(**kwargs)
            
            self._states[key] = state
            self._setup_cleanup_if_needed(key, identifier.scope)
            
        return self._states[key]
    
    def broadcast_to_state(self, state_key: str, event_data: dict):
        """Broadcast SSE event to all connections watching this state"""
        if state_key in self._connections:
            for connection in self._connections[state_key]:
                connection.send_event(event_data)
```

## Requirement 2: Authentication and Authorization System

### 2.1 Authentication Decorators
```python
from functools import wraps
from typing import Optional, Callable, List

class AuthenticationError(Exception):
    pass

class AuthorizationError(Exception):
    pass

def requires_auth(func: Callable = None, *, 
                 permissions: Optional[List[str]] = None,
                 roles: Optional[List[str]] = None,
                 owner_only: bool = False):
    """
    Decorator for events requiring authentication/authorization
    
    @event(requires_auth=True)
    def update_profile(self, data: dict): ...
    
    @event(requires_auth=True, permissions=['admin.users'])
    def delete_user(self, user_id: int): ...
    
    @event(requires_auth=True, owner_only=True)
    def update_my_data(self, data: dict): ...
    """
    def decorator(event_func):
        @wraps(event_func)
        async def wrapper(self, *args, **kwargs):
            request = get_current_request()  # Get from context
            user = await get_current_user(request)
            
            if user is None:
                raise AuthenticationError("Authentication required")
            
            # Check permissions
            if permissions and not user.has_permissions(permissions):
                raise AuthorizationError(f"Missing permissions: {permissions}")
                
            # Check roles
            if roles and not user.has_roles(roles):
                raise AuthorizationError(f"Missing roles: {roles}")
                
            # Check ownership
            if owner_only and hasattr(self, 'user_id') and self.user_id != user.id:
                raise AuthorizationError("Access denied: owner only")
                
            return await event_func(self, *args, **kwargs)
        
        wrapper._auth_config = {
            'required': True,
            'permissions': permissions or [],
            'roles': roles or [],
            'owner_only': owner_only
        }
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)
```

### 2.2 User Context Management
```python
class UserContext:
    def __init__(self, user_id: int, username: str, roles: List[str], permissions: List[str]):
        self.id = user_id
        self.username = username
        self.roles = roles
        self.permissions = permissions
    
    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or 'admin' in self.roles
    
    def has_role(self, role: str) -> bool:
        return role in self.roles

# Context variable for current request
from contextvars import ContextVar
current_user: ContextVar[Optional[UserContext]] = ContextVar('current_user', default=None)
current_request: ContextVar[Optional[Request]] = ContextVar('current_request', default=None)

async def get_current_user(request: Request) -> Optional[UserContext]:
    """Extract user from session/JWT/etc."""
    # Implementation depends on your auth system
    session = request.session
    user_id = session.get('user_id')
    if user_id:
        # Load user from database/cache
        return await load_user_by_id(user_id)
    return None
```

## Requirement 3: Automated State Dependency Injection

### 3.1 State Provider System
```python
class StateProvider:
    def __init__(self):
        self.state_configs: dict[type[ReactiveState], StateConfig] = {}
        self.registry = StateRegistry()
    
    def register_state(self, state_cls: type[ReactiveState], config: StateConfig):
        """Register state class with configuration"""
        self.state_configs[state_cls] = config
    
    async def get_state(self, state_cls: type[ReactiveState], request: Request, **kwargs) -> ReactiveState:
        """Automatically resolve state based on configuration"""
        config = self.state_configs.get(state_cls)
        if not config:
            raise ValueError(f"State {state_cls.__name__} not registered")
        
        # Create identifier based on config
        identifier = await self._create_identifier(config, request, **kwargs)
        
        # Get or create state
        state = self.registry.get_state(identifier, state_cls, **kwargs)
        
        # Set up SSE connection tracking
        self._track_connection(identifier.generate_key(), request)
        
        return state
    
    async def _create_identifier(self, config: StateConfig, request: Request, **kwargs) -> StateIdentifier:
        user = await get_current_user(request)
        session_id = request.session.get('session_id', str(uuid.uuid4()))
        
        return StateIdentifier(
            scope=config.scope,
            cls_name=config.state_cls.__name__,
            user_id=user.id if user else None,
            session_id=session_id,
            component_id=kwargs.get('component_id'),
            record_id=kwargs.get('record_id')
        )

class StateConfig:
    def __init__(self, 
                 state_cls: type[ReactiveState],
                 scope: StateScope = StateScope.SESSION,
                 ttl: Optional[int] = None,
                 auto_persist: bool = False,
                 requires_auth: bool = False):
        self.state_cls = state_cls
        self.scope = scope
        self.ttl = ttl  # Time to live in seconds
        self.auto_persist = auto_persist
        self.requires_auth = requires_auth
```

### 3.2 FastHTML App Integration
```python
# In app/main.py - Enhanced setup
from faststate import StateProvider, StateConfig, StateScope

# Create state provider
state_provider = StateProvider()

# Register state configurations
state_provider.register_state(
    UserProfileState,
    StateConfig(scope=StateScope.USER, auto_persist=True, requires_auth=True)
)

state_provider.register_state(
    GlobalSettingsState,
    StateConfig(scope=StateScope.GLOBAL, requires_auth=True, permissions=['admin'])
)

state_provider.register_state(
    CartState,
    StateConfig(scope=StateScope.SESSION, ttl=3600)  # 1 hour TTL
)

state_provider.register_state(
    ProductState,
    StateConfig(scope=StateScope.RECORD)  # Tied to product records
)

# Add to FastHTML app
app, rt = fast_app(
    static_path="assets",
    state_provider=state_provider,  # Inject state provider
    # ... other config
)

# Enhanced route decorators
@rt('/')
async def index(request: Request, 
               cart: CartState = Depends(state_provider.get_state),
               settings: GlobalSettingsState = Depends(state_provider.get_state)):
    """States automatically injected based on registration"""
    return render_page(cart, settings)

@rt('/profile')
async def profile(request: Request,
                 profile: UserProfileState = Depends(state_provider.get_state)):
    """User profile state - requires authentication"""
    return render_profile(profile)

@rt('/product/{product_id}')
async def product_detail(request: Request, product_id: int,
                        product: ProductState = Depends(state_provider.get_state)):
    """Product state tied to specific record"""
    return render_product(product)
```

## Requirement 4: Enhanced SSE Connection Management

### 4.1 Connection Tracking and Broadcasting
```python
class SSEConnection:
    def __init__(self, connection_id: str, response_stream, user_id: Optional[int] = None):
        self.id = connection_id
        self.stream = response_stream
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.subscribed_states: set[str] = set()
    
    async def send_event(self, event_data: dict):
        """Send SSE event to this connection"""
        try:
            yield SSE.merge_signals(event_data)
            self.last_ping = datetime.utcnow()
        except Exception:
            # Connection closed, mark for cleanup
            self.stream = None

class SSEManager:
    def __init__(self):
        self.connections: dict[str, SSEConnection] = {}
        self.state_subscriptions: dict[str, set[str]] = {}  # state_key -> connection_ids
    
    def add_connection(self, connection: SSEConnection, state_keys: List[str]):
        """Add connection and subscribe to states"""
        self.connections[connection.id] = connection
        
        for state_key in state_keys:
            if state_key not in self.state_subscriptions:
                self.state_subscriptions[state_key] = set()
            self.state_subscriptions[state_key].add(connection.id)
            connection.subscribed_states.add(state_key)
    
    async def broadcast_to_state(self, state_key: str, event_data: dict, exclude_user: Optional[int] = None):
        """Broadcast event to all connections subscribed to a state"""
        if state_key not in self.state_subscriptions:
            return
            
        dead_connections = []
        for conn_id in self.state_subscriptions[state_key]:
            connection = self.connections.get(conn_id)
            if not connection or not connection.stream:
                dead_connections.append(conn_id)
                continue
                
            # Skip if excluding specific user
            if exclude_user and connection.user_id == exclude_user:
                continue
                
            try:
                await connection.send_event(event_data)
            except Exception:
                dead_connections.append(conn_id)
        
        # Clean up dead connections
        for conn_id in dead_connections:
            self.remove_connection(conn_id)
    
    async def cleanup_stale_connections(self):
        """Remove connections that haven't been active"""
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        stale_connections = [
            conn_id for conn_id, conn in self.connections.items()
            if conn.last_ping < cutoff
        ]
        
        for conn_id in stale_connections:
            self.remove_connection(conn_id)
```

### 4.2 Global vs Session State Broadcasting
```python
class StateEventHandler:
    def __init__(self, sse_manager: SSEManager, state_provider: StateProvider):
        self.sse_manager = sse_manager
        self.state_provider = state_provider
    
    async def handle_state_change(self, state_key: str, changed_data: dict, 
                                 user_id: Optional[int] = None):
        """Handle state change and determine broadcast scope"""
        
        # Parse state scope from key
        scope = state_key.split(':')[0]
        
        if scope == StateScope.GLOBAL.value:
            # Broadcast to ALL connected users
            await self.sse_manager.broadcast_to_state(state_key, changed_data)
            
        elif scope == StateScope.SESSION.value:
            # Broadcast only to connections from same session
            await self.sse_manager.broadcast_to_state(state_key, changed_data)
            
        elif scope == StateScope.USER.value:
            # Broadcast to all sessions of the same user
            user_state_pattern = f"session:*:user{user_id}:*"
            matching_states = self._find_matching_states(user_state_pattern)
            for state in matching_states:
                await self.sse_manager.broadcast_to_state(state, changed_data)
```

## Requirement 5: Implementation Roadmap

### Phase 1: Core State Management (Week 1-2)
1. Implement `StateScope` enum and `StateIdentifier` class
2. Create enhanced `StateRegistry` with hierarchical keys
3. Update `_get_state` function to use new system
4. Add basic connection tracking

### Phase 2: Authentication Layer (Week 3)
1. Implement `requires_auth` decorator system
2. Add user context management
3. Create permission/role checking
4. Update event handlers to check auth

### Phase 3: Dependency Injection (Week 4)
1. Create `StateProvider` and `StateConfig` classes
2. Integrate with FastHTML app initialization
3. Add `Depends()` support for automatic state injection
4. Update existing routes to use new system

### Phase 4: Advanced SSE Management (Week 5)
1. Implement `SSEConnection` and `SSEManager` classes
2. Add connection cleanup and health monitoring
3. Implement scope-based broadcasting
4. Add connection pooling and optimization

### Phase 5: Production Features (Week 6)
1. Add state persistence and caching
2. Implement auto-cleanup for temporary states
3. Add monitoring and metrics
4. Performance optimization and testing

## Benefits of This Architecture

1. **Scalability**: Proper state scoping prevents memory leaks and supports multiple users
2. **Security**: Built-in authentication and authorization for all state operations
3. **Developer Experience**: Automatic state injection eliminates boilerplate
4. **Flexibility**: Support for global, session, user, component, and record-based states
5. **Production Ready**: Connection management, cleanup, monitoring, and error handling

This architecture positions FastState as a truly production-ready reactive state management system for Python web applications.