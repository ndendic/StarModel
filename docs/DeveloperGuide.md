# FastState Developer Implementation Guide

This guide provides step-by-step instructions for implementing FastState in your applications, from basic setup to advanced patterns.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Implementation](#basic-implementation)
3. [State Scopes and Configuration](#state-scopes-and-configuration)
4. [Authentication Integration](#authentication-integration)
5. [Advanced Patterns](#advanced-patterns)
6. [Performance Optimization](#performance-optimization)
7. [Testing Strategies](#testing-strategies)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Installation and Setup

```bash
# Install dependencies
pip install fasthtml datastar-py sqlmodel

# Or with uv
uv add fasthtml datastar-py sqlmodel
```

### 2. Initialize FastState

```python
from fasthtml.common import *
from faststate import (
    ReactiveState, event, StateScope, StateConfig, 
    state_registry, initialize_faststate
)

# Initialize FastState integration
initialize_faststate()

# Create FastHTML app
app, rt = fast_app()
```

### 3. Define Your First State

```python
class CounterState(ReactiveState):
    """Simple counter state for demonstration."""
    count: int = 0
    message: str = "Welcome to FastState!"
    
    @event
    def increment(self, amount: int = 1):
        """Increment counter by specified amount."""
        self.count += amount
    
    @event
    def reset(self):
        """Reset counter to zero."""
        self.count = 0
        self.message = "Counter reset!"
    
    @event("/custom-endpoint")
    def custom_action(self, text: str):
        """Custom endpoint with custom path."""
        self.message = f"Custom: {text}"
```

### 4. Register State

```python
# Register with default session scope
state_registry.register(
    CounterState,
    StateConfig(scope=StateScope.SESSION)
)
```

### 5. Create Routes with Automatic Injection

```python
@rt('/')
def index(counter: CounterState):
    """Main page with automatic state injection."""
    return Titled("FastState Demo",
        Div(
            # Display current state
            H1("Counter Demo"),
            P(f"Count: {counter.count}"),
            P(f"Message: {counter.message}"),
            
            # Interactive controls
            Button("Increment", onclick="increment({amount: 1})"),
            Button("Add 5", onclick="increment({amount: 5})"),
            Button("Reset", onclick="reset()"),
            
            # State signals for reactive updates
            data_signals=json.dumps(counter.model_dump()),
            id="updates"
        )
    )
```

### 6. Run Your Application

```python
if __name__ == "__main__":
    serve(reload=True)
```

---

## Basic Implementation

### State Class Design Patterns

#### 1. Simple Data State

```python
class UserPreferences(ReactiveState):
    """User preferences state."""
    theme: str = "light"
    language: str = "en"
    notifications: bool = True
    
    @event
    def update_theme(self, theme: str):
        """Update user theme preference."""
        if theme in ["light", "dark", "auto"]:
            self.theme = theme
        else:
            # Return error without updating state
            return Div("Invalid theme", cls="error")
    
    @event
    def toggle_notifications(self):
        """Toggle notification preference."""
        self.notifications = not self.notifications
```

#### 2. Form State Management

```python
class ContactForm(ReactiveState):
    """Contact form state with validation."""
    name: str = ""
    email: str = ""
    message: str = ""
    errors: dict = Field(default_factory=dict)
    is_submitting: bool = False
    
    @event
    def update_field(self, field: str, value: str):
        """Update form field and clear related errors."""
        setattr(self, field, value)
        if field in self.errors:
            del self.errors[field]
    
    @event
    def validate_and_submit(self):
        """Validate form and submit if valid."""
        self.errors = {}
        
        # Validation
        if not self.name.strip():
            self.errors["name"] = "Name is required"
        if not self.email or "@" not in self.email:
            self.errors["email"] = "Valid email is required"
        if len(self.message) < 10:
            self.errors["message"] = "Message must be at least 10 characters"
        
        if self.errors:
            return  # Return early if validation fails
        
        # Submit logic
        self.is_submitting = True
        try:
            # Simulate API call
            submit_contact_form(self.name, self.email, self.message)
            # Reset form on success
            self.name = self.email = self.message = ""
            self.errors = {"success": "Message sent successfully!"}
        except Exception as e:
            self.errors = {"submit": f"Failed to send: {str(e)}"}
        finally:
            self.is_submitting = False
```

#### 3. Shopping Cart State

```python
class ShoppingCart(ReactiveState):
    """Shopping cart state with items management."""
    items: List[dict] = Field(default_factory=list)
    total: float = 0.0
    discount: float = 0.0
    
    def _calculate_total(self):
        """Calculate cart total."""
        subtotal = sum(item["price"] * item["quantity"] for item in self.items)
        self.total = subtotal - self.discount
    
    @event
    def add_item(self, product_id: int, name: str, price: float, quantity: int = 1):
        """Add item to cart."""
        # Check if item already exists
        for item in self.items:
            if item["product_id"] == product_id:
                item["quantity"] += quantity
                self._calculate_total()
                return
        
        # Add new item
        self.items.append({
            "product_id": product_id,
            "name": name,
            "price": price,
            "quantity": quantity
        })
        self._calculate_total()
    
    @event
    def remove_item(self, product_id: int):
        """Remove item from cart."""
        self.items = [item for item in self.items if item["product_id"] != product_id]
        self._calculate_total()
    
    @event
    def update_quantity(self, product_id: int, quantity: int):
        """Update item quantity."""
        if quantity <= 0:
            self.remove_item(product_id)
            return
        
        for item in self.items:
            if item["product_id"] == product_id:
                item["quantity"] = quantity
                break
        
        self._calculate_total()
    
    @event
    def apply_discount(self, discount_code: str):
        """Apply discount code."""
        # Validate discount code
        discount_amount = validate_discount_code(discount_code)
        if discount_amount:
            self.discount = discount_amount
            self._calculate_total()
        else:
            return Div("Invalid discount code", cls="error")
```

### Route Integration Patterns

#### 1. Basic Route with State

```python
@rt('/dashboard')
def dashboard(user_prefs: UserPreferences, cart: ShoppingCart):
    """Dashboard with multiple state injections."""
    return Titled("Dashboard",
        Div(
            # User preferences section
            Section(
                H2("Preferences"),
                P(f"Theme: {user_prefs.theme}"),
                Button("Toggle Dark Mode", 
                       onclick="update_theme({theme: 'dark'})"),
                data_signals=json.dumps(user_prefs.model_dump()),
                id="preferences"
            ),
            
            # Shopping cart section
            Section(
                H2("Shopping Cart"),
                P(f"Items: {len(cart.items)}"),
                P(f"Total: ${cart.total:.2f}"),
                data_signals=json.dumps(cart.model_dump()),
                id="cart"
            )
        )
    )
```

#### 2. Conditional State Injection

```python
@rt('/profile')
def profile(req: Request, sess: dict, profile: UserProfile, auth: str = None):
    """Profile page with auth-dependent state access."""
    if not auth:
        return RedirectResponse('/login')
    
    # State automatically injected for authenticated users
    return Titled("Profile",
        Div(
            H1(f"Welcome, {profile.name}"),
            Form(
                Input(value=profile.name, name="name"),
                Input(value=profile.email, name="email"),
                Button("Update Profile", type="submit"),
                data_on_submit="update_profile()"
            ),
            data_signals=json.dumps(profile.model_dump()),
            id="profile-updates"
        )
    )
```

---

## State Scopes and Configuration

### SESSION Scope (Default)

Best for user-specific data that doesn't need to persist across sessions.

```python
class ShoppingSession(ReactiveState):
    """Session-scoped shopping state."""
    viewed_products: List[int] = Field(default_factory=list)
    current_category: str = "all"
    search_query: str = ""

# Register with session scope
state_registry.register(
    ShoppingSession,
    StateConfig(scope=StateScope.SESSION)
)
```

**Use Cases**:
- Shopping carts
- Form data
- UI preferences
- Search filters

### USER Scope

For data that should persist across user sessions.

```python
class UserProfile(ReactiveState):
    """User-scoped persistent profile."""
    name: str = ""
    email: str = ""
    avatar_url: str = ""
    preferences: dict = Field(default_factory=dict)
    
    @event
    def update_profile(self, name: str, email: str):
        """Update user profile information."""
        self.name = name
        self.email = email

# Register with user scope
state_registry.register(
    UserProfile,
    StateConfig(scope=StateScope.USER)
)
```

**Use Cases**:
- User profiles
- Account settings
- Saved preferences
- User-specific configurations

### GLOBAL Scope

For application-wide shared state.

```python
class AppSettings(ReactiveState):
    """Global application settings."""
    maintenance_mode: bool = False
    announcement: str = ""
    feature_flags: dict = Field(default_factory=dict)
    
    @event
    def toggle_maintenance(self):
        """Toggle maintenance mode."""
        self.maintenance_mode = not self.maintenance_mode
    
    @event
    def update_announcement(self, message: str):
        """Update global announcement."""
        self.announcement = message

# Register with global scope
state_registry.register(
    AppSettings,
    StateConfig(scope=StateScope.GLOBAL)
)
```

**Use Cases**:
- System-wide settings
- Feature flags
- Global counters
- System status

### RECORD Scope

For data tied to specific database records.

```python
class DocumentEditor(ReactiveState):
    """Record-scoped document editing state."""
    document_id: int = 0
    content: str = ""
    last_saved: Optional[datetime] = None
    is_dirty: bool = False
    collaborators: List[str] = Field(default_factory=list)
    
    @event
    def update_content(self, content: str):
        """Update document content."""
        self.content = content
        self.is_dirty = True
    
    @event
    def save_document(self):
        """Save document to database."""
        # Save logic here
        save_document(self.document_id, self.content)
        self.last_saved = datetime.now()
        self.is_dirty = False

# Register with record scope and auto-persistence
state_registry.register(
    DocumentEditor,
    StateConfig(
        scope=StateScope.RECORD,
        auto_persist=True,
        ttl=3600  # 1 hour TTL
    )
)
```

**Route Usage**:
```python
@rt('/edit/{document_id}')
def edit_document(document_id: int, editor: DocumentEditor):
    """Document editor with record-scoped state."""
    # State automatically scoped to document_id
    return Titled(f"Editing Document {document_id}",
        Div(
            TextArea(editor.content, data_bind="$content"),
            Button("Save", onclick="save_document()",
                   disabled=not editor.is_dirty),
            data_signals=json.dumps(editor.model_dump()),
            id="editor"
        )
    )
```

---

## Authentication Integration

FastState uses FastHTML's standard beforeware pattern for authentication.

### Basic Authentication Setup

```python
def auth_beforeware(req, sess):
    """Simple session-based authentication."""
    # Check for user in session
    user_id = sess.get('user_id')
    if user_id:
        return user_id  # Return user identifier
    
    # Check for API key in headers
    api_key = req.headers.get('X-API-Key')
    if api_key:
        user = validate_api_key(api_key)
        if user:
            return user.id
    
    return None  # Not authenticated

# Apply to FastHTML app
app, rt = fast_app(before=auth_beforeware)
```

### Route-Level Authorization

```python
@rt('/admin')
def admin_panel(settings: AppSettings, auth: str = None):
    """Admin panel with authorization check."""
    if not auth or not is_admin(auth):
        return RedirectResponse('/login')
    
    return Titled("Admin Panel",
        Div(
            H1("System Administration"),
            Button("Toggle Maintenance", 
                   onclick="toggle_maintenance()"),
            data_signals=json.dumps(settings.model_dump()),
            id="admin"
        )
    )

def is_admin(user_id: str) -> bool:
    """Check if user has admin privileges."""
    user = get_user(user_id)
    return user and 'admin' in user.roles
```

### User-Scoped State with Authentication

```python
class UserDashboard(ReactiveState):
    """User-specific dashboard state."""
    widgets: List[dict] = Field(default_factory=list)
    layout: str = "grid"
    notifications: List[dict] = Field(default_factory=list)
    
    @event
    def add_widget(self, widget_type: str, config: dict):
        """Add widget to dashboard."""
        self.widgets.append({
            "id": str(uuid.uuid4()),
            "type": widget_type,
            "config": config,
            "created_at": datetime.now().isoformat()
        })

# Register with user scope
state_registry.register(
    UserDashboard,
    StateConfig(scope=StateScope.USER)
)

@rt('/dashboard')
def dashboard(dash: UserDashboard, auth: str = None):
    """User dashboard requiring authentication."""
    if not auth:
        return RedirectResponse('/login')
    
    return render_dashboard(dash)
```

### Middleware-Based Authorization

```python
def require_permission(permission: str):
    """Decorator requiring specific permission."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract auth from kwargs
            auth = kwargs.get('auth')
            if not auth or not user_has_permission(auth, permission):
                return Div("Access Denied", cls="error")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rt('/sensitive-data')
@require_permission('read_sensitive_data')
def sensitive_data(data: SensitiveDataState, auth: str = None):
    """Route requiring specific permission."""
    return render_sensitive_data(data)
```

---

## Advanced Patterns

### Custom Event Responses

```python
class NotificationState(ReactiveState):
    """State with custom event responses."""
    messages: List[dict] = Field(default_factory=list)
    
    @event(selector="#notifications", merge_mode="append")
    def add_notification(self, message: str, type: str = "info"):
        """Add notification with custom HTML response."""
        notification = {
            "id": str(uuid.uuid4()),
            "message": message,
            "type": type,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(notification)
        
        # Return custom HTML fragment
        return Div(
            Span(message),
            Button("×", onclick=f"remove_notification({{id: '{notification['id']}'}})",
                   cls="close-btn"),
            cls=f"notification notification-{type}",
            id=f"notification-{notification['id']}"
        )
    
    @event(selector=".notification", merge_mode="delete")
    def remove_notification(self, id: str):
        """Remove notification with delete merge mode."""
        self.messages = [msg for msg in self.messages if msg["id"] != id]
        # Return empty response - deletion handled by selector
        return ""
```

### Async Event Handlers

```python
class AsyncDataProcessor(ReactiveState):
    """State with async event processing."""
    status: str = "idle"
    progress: float = 0.0
    result: Optional[dict] = None
    
    @event
    async def process_data(self, data_url: str):
        """Async data processing with progress updates."""
        self.status = "downloading"
        self.progress = 0.0
        
        # Download data
        async with httpx.AsyncClient() as client:
            response = await client.get(data_url)
            data = response.json()
        
        self.progress = 0.3
        self.status = "processing"
        
        # Process data in chunks
        results = []
        for i, chunk in enumerate(data):
            result = await process_chunk(chunk)
            results.append(result)
            self.progress = 0.3 + (0.7 * (i + 1) / len(data))
        
        self.status = "completed"
        self.progress = 1.0
        self.result = {"items": results, "total": len(results)}
```

### State Composition

```python
class CompositeState(ReactiveState):
    """State that composes multiple sub-states."""
    user_data: dict = Field(default_factory=dict)
    app_settings: dict = Field(default_factory=dict)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize sub-states if needed
        self._user_state = None
        self._settings_state = None
    
    def get_user_state(self, req: Request, sess: dict, auth: str) -> UserProfile:
        """Get composed user state."""
        if not self._user_state:
            self._user_state = state_registry.resolve_state(
                UserProfile, req, sess, auth
            )
        return self._user_state
    
    @event
    def sync_user_data(self, req: Request, sess: dict, auth: str):
        """Sync data from user state."""
        user_state = self.get_user_state(req, sess, auth)
        self.user_data = user_state.model_dump()
```

### Dynamic State Registration

```python
def register_plugin_states(plugin_config: dict):
    """Dynamically register states from plugin configuration."""
    for state_name, config in plugin_config.get('states', {}).items():
        # Create dynamic state class
        state_class = create_dynamic_state_class(state_name, config)
        
        # Register with appropriate scope
        scope = StateScope(config.get('scope', 'session'))
        state_registry.register(
            state_class,
            StateConfig(
                scope=scope,
                ttl=config.get('ttl'),
                auto_persist=config.get('auto_persist', False)
            )
        )

def create_dynamic_state_class(name: str, config: dict) -> Type[ReactiveState]:
    """Create state class from configuration."""
    attrs = {}
    
    # Add fields from config
    for field_name, field_config in config.get('fields', {}).items():
        field_type = eval(field_config['type'])  # In production, use safer type resolution
        default_value = field_config.get('default')
        attrs[field_name] = field_type if default_value is None else default_value
    
    # Add methods from config
    for method_name, method_config in config.get('methods', {}).items():
        method = create_dynamic_method(method_config)
        attrs[method_name] = event(method)
    
    # Create class
    return type(name, (ReactiveState,), attrs)
```

---

## Performance Optimization

### State Caching Strategies

```python
# Configure TTL for automatic cleanup
state_registry.register(
    ExpensiveState,
    StateConfig(
        scope=StateScope.SESSION,
        ttl=1800  # 30 minutes
    )
)

# Manual cache management
def cleanup_expired_states():
    """Clean up expired state instances."""
    current_time = time.time()
    expired_keys = []
    
    for key, state in state_registry._state_instances.items():
        if hasattr(state, '_created_at'):
            if current_time - state._created_at > state._ttl:
                expired_keys.append(key)
    
    for key in expired_keys:
        del state_registry._state_instances[key]
```

### Efficient SSE Updates

```python
class OptimizedState(ReactiveState):
    """State optimized for minimal SSE updates."""
    # Group related fields to reduce update frequency
    user_info: dict = Field(default_factory=dict)
    ui_state: dict = Field(default_factory=dict)
    
    @event
    def batch_update(self, updates: dict):
        """Batch multiple updates to reduce SSE traffic."""
        # Collect all changes before applying
        for field, value in updates.items():
            if hasattr(self, field):
                setattr(self, field, value)
        
        # Single SSE response for all changes
    
    @event
    def update_ui_only(self, ui_changes: dict):
        """Update only UI state to avoid full re-render."""
        self.ui_state.update(ui_changes)
        
        # Return targeted update
        return f"event: datastar-merge-signals\ndata: {json.dumps({'ui_state': self.ui_state})}\n\n"
```

### Database Integration

```python
class PersistentState(ReactiveState, table=True):
    """State with automatic database persistence."""
    __tablename__ = "user_states"
    
    # Database fields
    user_id: str = Field(foreign_key="users.id")
    state_data: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @event
    def save_to_db(self, session: Session):
        """Manually save state to database."""
        self.updated_at = datetime.now()
        session.add(self)
        session.commit()
    
    @classmethod
    def load_from_db(cls, user_id: str, session: Session):
        """Load state from database."""
        return session.query(cls).filter(cls.user_id == user_id).first()
```

---

## Testing Strategies

### Unit Testing States

```python
import pytest
from faststate import ReactiveState, event

class TestCounterState:
    def test_increment(self):
        """Test counter increment functionality."""
        counter = CounterState()
        assert counter.count == 0
        
        counter.increment(5)
        assert counter.count == 5
    
    def test_reset(self):
        """Test counter reset functionality."""
        counter = CounterState()
        counter.count = 10
        
        counter.reset()
        assert counter.count == 0
        assert counter.message == "Counter reset!"
    
    def test_event_response(self):
        """Test SSE response generation."""
        counter = CounterState()
        
        # Manually test event wrapper
        old_state = counter.model_dump()
        counter.count = 42
        new_state = counter.model_dump()
        
        response = counter._diff_and_events(old_state, new_state)
        assert "datastar-merge-signals" in response.body.decode()
```

### Integration Testing

```python
from fastapi.testclient import TestClient

def test_state_injection():
    """Test automatic state injection in routes."""
    client = TestClient(app)
    
    # Test route with state injection
    response = client.get("/dashboard")
    assert response.status_code == 200
    
    # Test event endpoint
    response = client.post("/CounterState/increment", data={"amount": "5"})
    assert response.status_code == 200
    assert "datastar-merge-signals" in response.text

def test_state_persistence():
    """Test state persistence across requests."""
    client = TestClient(app)
    
    # First request - increment counter
    with client.session() as session:
        response = session.post("/CounterState/increment", data={"amount": "1"})
        
        # Second request - check persistence
        response = session.get("/dashboard")
        assert "1" in response.text  # Counter should be persisted
```

### Mock Testing

```python
from unittest.mock import Mock, patch

def test_state_registry_mocking():
    """Test with mocked state registry."""
    mock_state = Mock(spec=CounterState)
    mock_state.count = 42
    mock_state.model_dump.return_value = {"count": 42}
    
    with patch('faststate.state_registry.resolve_state', return_value=mock_state):
        # Test route behavior with mocked state
        response = client.get("/dashboard")
        assert "42" in response.text
```

---

## Troubleshooting

### Common Issues

#### 1. State Not Injected

**Problem**: Route function receives `None` for state parameter.

**Solutions**:
```python
# Check state registration
assert state_registry.is_state_type(MyState)

# Verify initialization
assert initialize_faststate() == True

# Check function signature
def my_route(my_state: MyState):  # Must have type annotation
    pass
```

#### 2. SSE Events Not Received

**Problem**: Client doesn't receive state updates.

**Solutions**:
```python
# Ensure data-signals attribute is set
Div(data_signals=json.dumps(state.model_dump()), id="updates")

# Check event endpoint registration
# Events should be accessible at /ClassName/method_name

# Verify Datastar script is loaded
Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0/bundles/datastar.js")
```

#### 3. Authentication Issues

**Problem**: User-scoped states fail with authentication errors.

**Solutions**:
```python
# Ensure beforeware returns user identifier
def auth_beforeware(req, sess):
    return sess.get('user_id')  # Must not be None for USER scope

# Check route parameter order
def route(state: UserState, auth: str = None):  # auth must be optional
    pass
```

#### 4. Memory Leaks

**Problem**: State instances accumulate in memory.

**Solutions**:
```python
# Configure TTL for automatic cleanup
StateConfig(scope=StateScope.SESSION, ttl=3600)

# Implement manual cleanup
def cleanup_sessions():
    expired_sessions = get_expired_sessions()
    for session_id in expired_sessions:
        state_registry.clear_session_states(session_id)
```

### Debugging Tools

#### 1. State Registry Inspector

```python
def debug_state_registry():
    """Debug helper for state registry."""
    info = get_state_info()
    print(f"Registered states: {len(info['registered_states'])}")
    print(f"Cached instances: {info['cached_instances']}")
    
    for state_info in info['registered_states']:
        print(f"- {state_info['class_name']}: {state_info['scope']}")

# Add to route for debugging
@rt('/debug')
def debug_info():
    debug_state_registry()
    return "Debug info printed to console"
```

#### 2. SSE Response Logging

```python
def log_sse_response(func):
    """Decorator to log SSE responses."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        old_state = self.model_dump()
        result = func(self, *args, **kwargs)
        new_state = self.model_dump()
        
        # Log state changes
        changes = {k: v for k, v in new_state.items() if old_state.get(k) != v}
        if changes:
            logger.info(f"State changes in {func.__name__}: {changes}")
        
        return result
    return wrapper

# Apply to event methods
@event
@log_sse_response
def my_event(self, param: str):
    pass
```

#### 3. Performance Monitoring

```python
import time
from functools import wraps

def monitor_performance(func):
    """Monitor state operation performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        logger.info(f"{func.__name__} took {duration:.3f}s")
        return result
    return wrapper

# Apply to state resolution
@monitor_performance
def resolve_state(self, state_cls, req, sess, auth):
    pass
```

This comprehensive guide covers all aspects of implementing FastState in your applications. For more advanced use cases or specific questions, refer to the API documentation and examples.