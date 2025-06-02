"""
FastState Demo Application

This application demonstrates the FastState system with automatic
dependency injection and different state scopes.
Authentication is handled via FastHTML beforeware.
"""

import json
from fasthtml.common import *
from monsterui.all import *

# Import FastState components
from faststate import (
    State, event, StateScope, StateConfig, state_registry, sse_manager, persistence_manager,
    MemoryStatePersistence, DatabaseStatePersistence
)

# Import existing routes and state routes for backward compatibility
from routes import rt as old_routes
from faststate.state import rt as state_rt

# Set up enhanced persistence backends
print("💾 Setting up persistence backends...")
try:
    # Add database persistence for production-like features
    db_persistence = DatabaseStatePersistence(database_url="sqlite:///faststate_demo.db")
    persistence_manager.add_backend("database", db_persistence)
    print("✅ Database persistence backend added")
except Exception as e:
    print(f"⚠ Database persistence not available: {e}")

# Add memory persistence for demo
memory_persistence = MemoryStatePersistence()
persistence_manager.add_backend("memory", memory_persistence)
print("✅ Memory persistence backend added")

# =============================================================================
# STATE DEFINITIONS WITH DIFFERENT SCOPES
# =============================================================================

class MyState(State):
    """Session-scoped state - each user session gets its own instance."""
    myInt: int = 0
    myStr: str = "Hello"
    tick_count: int = 0

    @event
    def increment(self, amount: int):
        self.myInt += amount

    @event("/decrement")
    def decrement(self, amount: int):
        self.myInt -= amount

    @event("/reset")
    def reset(self):
        self.myInt = 0

    @event()
    def set_myStr(self, myStr: str):
        self.myStr = myStr
        
    @event(selector="#ticker-box", merge_mode="inner")
    def start_ticking(self):
        self.tick_count += 1
        return H4("Tick #", Span(data_text="$tick_count"), cls="text-red-500")


class UserProfileState(State):
    """User-scoped state - persists across sessions for authenticated users."""
    name: str = ""
    email: str = ""
    preferences: dict = {}
    
    @event(selector="#profile-updates")
    def update_profile(self, name: str, email: str):
        self.name = name
        self.email = email
        return Div(
                    H2("Profile Information", cls="text-xl font-bold mb-4"),
                    Div(
                        Div("Name: ", Span(data_text="$name"), cls="mb-2"),
                        Div("Email: ", Span(data_text="$email"), cls="mb-2"),
                        Div(f"User ID: {self.id}", cls="text-sm text-gray-600 mb-4"),
                        cls="bg-gray-100 p-4 rounded mb-6"
                    ),
                    cls="mb-6",
                    id="profile-updates"
                )
    
    @event
    def set_preference(self, key: str, value: str):
        if not isinstance(self.preferences, dict):
            self.preferences = {}
        self.preferences[key] = value
        return Div(f"Preference {key} set to {value}", cls="text-blue-600")


class GlobalSettingsState(State):
    """Global state - shared across all users (admin only)."""
    theme: str = "light"
    maintenance_mode: bool = False
    announcement: str = ""
    
    @event
    def toggle_maintenance(self):
        self.maintenance_mode = not self.maintenance_mode
        status = "enabled" if self.maintenance_mode else "disabled"
        return Div(f"Maintenance mode {status}!", cls="text-orange-600 font-bold")
    
    @event
    def set_announcement(self, message: str):
        self.announcement = message
        return Div("Announcement updated!", cls="text-blue-600 font-bold")
    
    @event
    def change_theme(self, theme: str):
        self.theme = theme
        return Div(f"Theme changed to {theme}!", cls="text-purple-600 font-bold")


class ProductState(State):
    """Record-scoped state - tied to specific product records."""
    name: str = ""
    price: float = 0.0
    description: str = ""
    in_stock: bool = True
    
    @event
    def update_product(self, name: str, price: float, description: str):
        self.name = name
        self.price = price
        self.description = description
        return Div("Product updated!", cls="text-green-600 font-bold")
    
    @event
    def toggle_stock(self):
        self.in_stock = not self.in_stock
        status = "in stock" if self.in_stock else "out of stock"
        return Div(f"Product marked as {status}!", cls="text-blue-600 font-bold")


class ChatState(State):
    """Global chat state for real-time collaboration demo."""
    messages: list = []
    active_users: int = 0
    last_message_id: int = 0
    
    @event(selector="#chat-messages", merge_mode="beforeend")
    def send_message(self, username: str, message: str):
        if not message.strip():
            return Div("Message cannot be empty", cls="text-red-500")
        
        self.last_message_id += 1
        new_message = {
            "id": self.last_message_id,
            "username": username or "Anonymous",
            "message": message.strip(),
            "timestamp": "now"
        }
        
        # Keep only last 10 messages for demo
        if len(self.messages) >= 10:
            self.messages = self.messages[-9:]
        self.messages.append(new_message)
        
        return Div(
            Div(
                Span(new_message["username"], cls="font-bold text-blue-600"),
                Span(f" ({new_message['timestamp']})", cls="text-xs text-gray-500 ml-2"),
                cls="mb-1"
            ),
            Div(new_message["message"], cls="text-gray-800"),
            cls="bg-blue-50 p-3 rounded mb-2 border-l-4 border-blue-500"
        )
    
    @event
    def join_chat(self, username: str):
        self.active_users += 1
        return Div(f"{username} joined the chat!", cls="text-green-600 font-bold")
    
    @event
    def leave_chat(self, username: str):
        if self.active_users > 0:
            self.active_users -= 1
        return Div(f"{username} left the chat.", cls="text-orange-600")


class CounterState(State):
    """Enhanced counter with persistence and real-time sync."""
    count: int = 0
    last_updated_by: str = ""
    update_count: int = 0
    
    @event
    def increment(self, amount: int = 1, user: str = "Anonymous"):
        self.count += amount
        self.last_updated_by = user
        self.update_count += 1
        return Div(f"Counter incremented by {amount} by {user}",id="message", cls="font-mono text-sm text-green-600")
    
    @event  
    def decrement(self, amount: int = 1, user: str = "Anonymous"):
        self.count -= amount
        self.last_updated_by = user
        self.update_count += 1
        return Div(f"Counter decremented by {amount} by {user}",id="message", cls="font-mono text-sm text-red-600")
    
    @event
    def reset(self, user: str = "Anonymous"):
        self.count = 0
        self.last_updated_by = user
        self.update_count += 1
        return Div(f"Counter reset by {user}",id="message", cls="font-mono text-sm text-blue-600")
    
    @event(selector="#counter-state")
    def push(self):
        return Div({"data-signals": json.dumps(self.model_dump()), "data-on-load__delay.1s": self.push()}, id="counter-state"),
    


# =============================================================================
# STATE REGISTRATION
# =============================================================================

print("📝 Registering state types...")

# Register MyState with session scope (default behavior)
state_registry.register(
    MyState,
    StateConfig(scope=StateScope.SESSION)
)

# Register UserProfileState with user scope and persistence
state_registry.register(
    UserProfileState,
    StateConfig(
        scope=StateScope.USER,
        auto_persist=True,
        persistence_backend="database",
        ttl=3600  # 1 hour cache
    )
)

# Register GlobalSettingsState with global scope and persistence
state_registry.register(
    GlobalSettingsState,
    StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="database"
    )
)

# Register ProductState with record scope and database persistence
state_registry.register(
    ProductState,
    StateConfig(
        scope=StateScope.RECORD, 
        auto_persist=True,
        persistence_backend="database",
        ttl=7200  # 2 hours cache
    )
)

# Register ChatState with global scope for real-time chat
state_registry.register(
    ChatState,
    StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="memory"  # Use memory for demo chat
    )
)

# Register CounterState with global scope and persistence
state_registry.register(
    CounterState,
    StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="database"
    )
)

print("✅ State registration complete!")

# =============================================================================
# AUTHENTICATION BEFOREWARE
# =============================================================================

def auth_beforeware(req, sess):
    """
    Simple authentication beforeware using FastHTML/Starlette pattern.
    This demonstrates how to handle auth outside of FastState.
    """
    # Simple demo auth - in real apps, integrate with your auth system
    auth = req.scope["user"] = sess.get("auth", None)
    if not auth:
        return RedirectResponse("/login", status_code=303)
beforeware = Beforeware(
    auth_beforeware,
    skip=[
        r"/favicon\.ico",
        r"/assets/.*",
        r".*\.css",
        r".*\.svg",
        r".*\.png",
        r".*\.jpg",
        r".*\.jpeg",
        r".*\.gif",
        r".*\.js",
        r"/login",
        r"/auth-demo",
        r"/api/.*",
    ],
)
# =============================================================================
# FASTHTML APP SETUP
# =============================================================================

custom_theme_css = Link(rel="stylesheet", href="/css/custom_theme.css", type="text/css")
monsterui_headers = Theme.claude.headers()
datastar_script = Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0-beta.11/bundles/datastar.js", type="module")

app, rt = fast_app(
    static_path="assets",
    live=True,
    pico=False,
    htmx=False,
    before=beforeware,  # Add auth beforeware
    hdrs=(
        monsterui_headers,
        custom_theme_css,
        datastar_script,
    ),
    htmlkw=dict(cls="bg-surface-light data-theme-claude dark:bg-surface-dark bg-background font-sans antialiased"),
)

# =============================================================================
# ENHANCED ROUTES WITH AUTOMATIC STATE INJECTION
# =============================================================================

@rt('/')
def index(req: Request, sess: dict, auth: str = None):
    """
    Main page demonstrating session-scoped state with simple .get() method.
    Clean and explicit state resolution!
    """
    if not auth:
        auth = sess.get('auth', None)
    
    # Simple, explicit state resolution
    my_state = MyState.get(req, sess, auth)
    return Titled("FastState Demo - Enhanced with DI",
        Main(
            # Welcome message
            Div(
                H1("🚀 FastState Demo", cls="text-4xl font-bold text-center mb-6"),
                P("Showcasing automatic dependency injection with different state scopes", 
                  cls="text-center text-gray-600 mb-8"),
                cls="mb-8"
            ),
            
            # State information
            Div(
                H2("📊 Current State Info", cls="text-2xl font-bold mb-4"),
                Div(
                    Div(f"Session ID: {req.cookies.get('session_', 'auto-generated')[:100]}", cls="font-mono text-sm"),
                    Div(f"Auth: {auth or 'Not authenticated'}", cls="font-mono text-sm"),
                    Div(f"State ID: {my_state.id}", cls="font-mono text-sm"),
                    cls="bg-gray-100 p-4 rounded mb-6"
                ),
                cls="mb-8"
            ),
            
            # State display and controls
            Div(data_signals=json.dumps(my_state.model_dump()), id="updates"),
            my_state,  # Uses __ft__ method for rendering
            
            # Interactive controls
            Div(
                H3("🎮 Interactive Controls", cls="text-xl font-bold mb-4"),
                Input(data_bind="$myStr", data_on_change=MyState.set_myStr(), 
                      cls="border rounded px-3 py-2 mb-4 w-full", placeholder="Edit text..."),
                      
                H4("Counter Controls", cls="font-bold mb-2"),
                Div(
                    Button("- Decrease", data_on_click=MyState.decrement(1), 
                           cls="bg-red-500 text-white px-4 py-2 rounded mr-2"),
                    Button("🔄 Reset", data_on_click=MyState.reset(), 
                           cls="bg-gray-500 text-white px-4 py-2 rounded mr-2"),
                    Button("+ Increase", data_on_click=MyState.increment(1), 
                           cls="bg-green-500 text-white px-4 py-2 rounded"),
                    cls="mb-4"
                ),
                
                H4("Ticker Demo", cls="font-bold mb-2"),
                Div(id="ticker-box", cls="bg-yellow-50 p-4 rounded mb-4 min-h-[60px]"),
                Button("Start Tick", data_on_click=MyState.start_ticking(), 
                       cls="bg-blue-500 text-white px-4 py-2 rounded"),
                cls="mb-8"
            ),
            
            # Navigation
            Div(
                H3("🔗 Navigation", cls="text-xl font-bold mb-4"),
                Div(
                    A("👤 User Profile", href="/profile", cls="bg-blue-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                    A("⚙️ Admin Panel", href="/admin", cls="bg-purple-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                    A("📦 Product Demo", href="/product/123", cls="bg-green-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                    A("💬 Real-time Chat", href="/chat", cls="bg-orange-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                    A("🔢 Global Counter", href="/counter", cls="bg-indigo-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                    A("📊 System Status", href="/status", cls="bg-cyan-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                    A("🔒 Login Demo", href="/login", cls="bg-gray-500 text-white px-4 py-2 rounded mb-2 inline-block"),
                ),
                cls="mb-8"
            ),
            
            cls="container mx-auto p-8 max-w-4xl"
        )
    )


@rt('/profile')
def profile(req: Request, sess: dict, auth: str = None):
    """
    User profile page with user-scoped state.
    Uses simple .get() method for state resolution.
    """
    # Simple, explicit state resolution
    profile = UserProfileState.get(req, sess, auth)
    
    return Titled("User Profile",
        Main(
            Div(
                H1("👤 User Profile", cls="text-3xl font-bold mb-6"),
                
                # Profile state display
                Div(data_signals=json.dumps(profile.model_dump()), id="profile-updates"),
                
                # Profile information
                Div(
                    H2("Profile Information", cls="text-xl font-bold mb-4"),
                    Div(
                        Div("Name: ", Span(data_text="$name"), cls="mb-2"),
                        Div("Email: ", Span(data_text="$email"), cls="mb-2"),
                        Div(f"User ID: {auth}", cls="text-sm text-gray-600 mb-4"),
                        cls="bg-gray-100 p-4 rounded mb-6"
                    ),
                    cls="mb-6",
                    id="profile-updates"
                ),
                
                # Profile form
                Div(
                    H3("Update Profile", cls="text-lg font-bold mb-4"),
                    Form(
                        Input(value=profile.name, name="name", placeholder="Full Name", 
                              data_bind="$name", cls="border rounded px-3 py-2 mb-3 w-full"),
                        Input(value=profile.email, name="email", placeholder="Email Address", 
                              data_bind="$email", cls="border rounded px-3 py-2 mb-3 w-full"),
                        Button("Update Profile", type="submit", data_on_click=UserProfileState.update_profile(),
                               cls="bg-blue-500 text-white px-6 py-2 rounded"),
                        data_on_submit=UserProfileState.update_profile()
                    ),
                    cls="mb-6"
                ),
                
                # Preferences
                Div(
                    H3("Preferences", cls="text-lg font-bold mb-4"),
                    Div("Current preferences: ", Pre(data_text="$preferences"), 
                        cls="bg-gray-100 p-4 rounded"),
                    cls="mb-6"
                ),
                
                # Navigation
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-2xl"
            )
        )
    )


@rt('/admin')
def admin_panel(req: Request, sess: dict, auth: str = None):
    """
    Admin panel with global state.
    Uses simple .get() method for state resolution.
    """
    # Simple, explicit state resolution
    settings = GlobalSettingsState.get(req, sess, auth)
    return Titled("Admin Panel",
        Main(
            Div(
                H1("⚙️ Admin Panel", cls="text-3xl font-bold mb-6"),
                
                # Global state display
                Div(data_signals=json.dumps(settings.model_dump()), id="admin-updates"),
                
                # System status
                Div(
                    H2("System Status", cls="text-xl font-bold mb-4"),
                    Div(
                        Div("Theme: ", Span(data_text="$theme"), cls="mb-2"),
                        Div("Maintenance Mode: ", Span(data_text="$maintenance_mode"), cls="mb-2"),
                        Div("Announcement: ", Span(data_text="$announcement"), cls="mb-2"),
                        cls="bg-gray-100 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Admin controls
                Div(
                    H3("Global Controls", cls="text-lg font-bold mb-4"),
                    
                    Div(
                        Button("Toggle Maintenance Mode", 
                               data_on_click=GlobalSettingsState.toggle_maintenance(),
                               cls="bg-orange-500 text-white px-4 py-2 rounded mr-2 mb-2"),
                        cls="mb-4"
                    ),
                    
                    Div(
                        Input(placeholder="System announcement...", name="message",
                              cls="border rounded px-3 py-2 mr-2 flex-1"),
                        Button("Set Announcement", 
                               data_on_click=GlobalSettingsState.set_announcement(),
                               cls="bg-blue-500 text-white px-4 py-2 rounded"),
                        cls="flex mb-4"
                    ),
                    
                    Div(
                        Button("Light Theme", 
                               data_on_click=GlobalSettingsState.change_theme("light"),
                               cls="bg-gray-200 text-gray-800 px-4 py-2 rounded mr-2"),
                        Button("Dark Theme", 
                               data_on_click=GlobalSettingsState.change_theme("dark"),
                               cls="bg-gray-800 text-white px-4 py-2 rounded"),
                        cls="mb-6"
                    ),
                    
                    cls="mb-6"
                ),
                
                # Navigation
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-2xl"
            )
        )
    )


@rt('/product/{record_id}')
def product_detail(req: Request, sess: dict, record_id: int, auth: str = None):
    """
    Product detail page with record-scoped state.
    Demonstrates state tied to specific database records.
    """
    # State automatically injected by FastHTML integration
    product = ProductState.get(req, sess, auth)

    # Initialize product data if empty (simulating database load)
    if not product.name:
        product.name = f"Sample Product {record_id}"
        product.price = 19.99
        product.description = f"This is a sample product with ID {record_id}"
    
    return Titled(f"Product {record_id}",
        Main(
            Div(
                H1(f"📦 Product {record_id}", cls="text-3xl font-bold mb-6"),
                
                # Product state display
                Div(data_signals=json.dumps(product.model_dump()), id="product-updates"),
                
                # Product information
                Div(
                    H2("Product Details", cls="text-xl font-bold mb-4"),
                    Div(
                        Div("Name: ", Span(data_text="$name"), cls="mb-2 font-bold"),
                        Div("Price: $", Span(data_text="$price"), cls="mb-2"),
                        Div("Description: ", Span(data_text="$description"), cls="mb-2"),
                        Div("In Stock: ", Span(data_text="$in_stock"), cls="mb-2"),
                        Div(f"Product ID: {record_id}", cls="text-sm text-gray-600"),
                        cls="bg-gray-100 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Product management (if user has permissions)
                Div(
                    H3("Product Management", cls="text-lg font-bold mb-4"),
                    Form(
                        Input(value=product.name, name="name", placeholder="Product Name", 
                              cls="border rounded px-3 py-2 mb-3 w-full"),
                        Input(value=product.price, name="price", placeholder="Price", type="number", step="0.01",
                              cls="border rounded px-3 py-2 mb-3 w-full"),
                        Input(value=product.description, name="description", placeholder="Description", 
                              cls="border rounded px-3 py-2 mb-3 w-full"),
                        Button("Update Product", type="submit", 
                               cls="bg-green-500 text-white px-6 py-2 rounded mr-2"),
                        data_on_submit=ProductState.update_product()
                    ),
                    Button("Toggle Stock Status", 
                           data_on_click=ProductState.toggle_stock(),
                           cls="bg-blue-500 text-white px-4 py-2 rounded mt-4"),
                    cls="mb-6"
                ),
                
                # Navigation
                Div(
                    A("← Back to Home", href="/", cls="text-blue-500 hover:underline mr-4"),
                    A("📦 Product 456", href="/product/456", cls="text-green-500 hover:underline mr-4"),
                    A("📦 Product 789", href="/product/789", cls="text-green-500 hover:underline"),
                ),
                
                cls="container mx-auto p-8 max-w-2xl"
            )
        )
    )


@rt('/chat')
def realtime_chat(req: Request, sess: dict, auth: str = None):
    """
    Real-time chat demo showcasing global state and SSE broadcasting.
    """
    chat = ChatState.get(req, sess, auth)
    username = auth or sess.get('auth', 'Anonymous')
    
    return Titled("Real-time Chat",
        Main(
            Div(
                H1("💬 Real-time Chat Demo", cls="text-3xl font-bold mb-6"),
                P("This demonstrates global state with real-time SSE broadcasting across all connected users.", 
                  cls="text-gray-600 mb-6"),
                
                # SSE Connection Setup
                Script("""
                    // Connect to SSE for real-time updates
                    const eventSource = new EventSource('/faststate/sse?states=ChatState');
                    eventSource.onmessage = function(event) {
                        console.log('SSE event received:', event.data);
                    };
                    
                    // Clean up on page unload
                    window.addEventListener('beforeunload', function() {
                        eventSource.close();
                    });
                """),
                
                # Chat state display
                Div(data_signals=json.dumps(chat.model_dump()), id="chat-state"),
                
                # Chat info
                Div(
                    H2("Chat Status", cls="text-xl font-bold mb-4"),
                    Div(
                        Div("Active Users: ", Span(data_text="$active_users"), cls="mb-2"),
                        Div("Total Messages: ", Span(str(len(chat.messages))), cls="mb-2"),
                        Div(f"Your Username: {username}", cls="mb-2 font-mono"),
                        cls="bg-gray-100 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Chat messages area
                Div(
                    H3("Messages", cls="text-lg font-bold mb-4"),
                    Div(
                        *[
                            Div(
                                Div(
                                    Span(msg["username"], cls="font-bold text-blue-600"),
                                    Span(f" ({msg['timestamp']})", cls="text-xs text-gray-500 ml-2"),
                                    cls="mb-1"
                                ),
                                Div(msg["message"], cls="text-gray-800"),
                                cls="bg-blue-50 p-3 rounded mb-2 border-l-4 border-blue-500"
                            ) for msg in chat.messages
                        ],
                        id="chat-messages",
                        cls="h-64 overflow-y-auto bg-white border rounded p-4 mb-4"
                    ),
                    cls="mb-6"
                ),
                
                # Chat input
                Div(
                    H3("Send Message", cls="text-lg font-bold mb-4"),
                    Form(
                        Input(value=username, name="username", placeholder="Username", 
                              cls="border rounded px-3 py-2 mr-2 w-32"),
                        Input(name="message", placeholder="Type your message...", 
                              cls="border rounded px-3 py-2 mr-2 flex-1"),
                        Button("Send", type="submit", 
                               cls="bg-blue-500 text-white px-6 py-2 rounded"),
                        data_on_submit=ChatState.send_message(),
                        cls="flex mb-4"
                    ),
                    cls="mb-6"
                ),
                
                # Chat actions
                Div(
                    Button("Join Chat", 
                           data_on_click=ChatState.join_chat(username),
                           cls="bg-green-500 text-white px-4 py-2 rounded mr-2"),
                    Button("Leave Chat", 
                           data_on_click=ChatState.leave_chat(username),
                           cls="bg-red-500 text-white px-4 py-2 rounded"),
                    cls="mb-6"
                ),
                
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-4xl"
            )
        )
    )


@rt('/counter')
def global_counter(req: Request, sess: dict, auth: str = None):
    """
    Global counter demo with persistence and real-time synchronization.
    """
    counter = CounterState.get(req, sess, auth)
    username = auth or sess.get('auth', 'Anonymous')
    
    return Titled("Global Counter",
        Div({"data-signals": json.dumps(counter.model_dump()), "data-on-load__delay.1s": counter.push()}, id="counter-state"),
        Main(
            Div(
                H1("🔢 Global Counter Demo", cls="text-3xl font-bold mb-6"),
                P("This counter is shared globally across all users and persisted to database.", 
                  cls="text-gray-600 mb-6"),
                
                # Counter display
                Div(
                    H2("Current Count", cls="text-xl font-bold mb-4"),
                    Div(
                        Div(
                            Span("Count: ", cls="text-2xl"),
                            Span(data_text="$count", cls="text-4xl font-bold text-blue-600"),
                            cls="text-center mb-4"
                        ),
                        Div("Last updated by: ", Span(data_text="$last_updated_by"), cls="mb-2"),
                        Div("Total updates: ", Span(data_text="$update_count"), cls="mb-2"),
                        Div(f"Current user: {username}", cls="font-mono text-sm text-gray-600"),
                        Div(id="message", cls="font-mono text-sm text-gray-600"),
                        cls="bg-gray-100 p-6 rounded mb-6 text-center"
                    ),
                    cls="mb-6"
                ),
                
                # Counter controls
                Div(
                    H3("Counter Controls", cls="text-lg font-bold mb-4"),
                    Div(
                        Button("-10", 
                               data_on_click=CounterState.decrement(10, username),
                               cls="bg-red-600 text-white px-4 py-2 rounded mr-2"),
                        Button("-1", 
                               data_on_click=CounterState.decrement(1, username),
                               cls="bg-red-400 text-white px-4 py-2 rounded mr-2"),
                        Button("Reset", 
                               data_on_click=CounterState.reset(username),
                               cls="bg-gray-500 text-white px-4 py-2 rounded mr-2"),
                        Button("+1", 
                               data_on_click=CounterState.increment(1, username),
                               cls="bg-green-400 text-white px-4 py-2 rounded mr-2"),
                        Button("+10", 
                               data_on_click=CounterState.increment(10, username),
                               cls="bg-green-600 text-white px-4 py-2 rounded"),
                        cls="text-center mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Custom increment
                Div(
                    H3("Custom Increment", cls="text-lg font-bold mb-4"),
                    Form(
                        Input(name="amount", placeholder="Amount", type="number", value="1",
                              cls="border rounded px-3 py-2 mr-2 w-24"),
                        Button("Add", type="submit", 
                               cls="bg-blue-500 text-white px-4 py-2 rounded mr-2"),
                        data_on_submit=CounterState.increment(user=username),
                        cls="mb-6"
                    ),
                    cls="mb-6"
                ),
                
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-3xl"
            )
        )
    )


@rt('/status')
def system_status(req: Request, sess: dict, auth: str = None):
    """
    System status page showing SSE connections, persistence stats, and more.
    """
    # Get SSE connection stats
    sse_stats = sse_manager.get_connection_stats()
    
    # Get state registry stats
    cached_states = len(state_registry.get_cached_instances())
    
    return Titled("System Status",
        Main(
            Div(
                H1("📊 System Status", cls="text-3xl font-bold mb-6"),
                P("Real-time system monitoring and statistics.", 
                  cls="text-gray-600 mb-6"),
                
                # SSE Connection Stats
                Div(
                    H2("SSE Connection Statistics", cls="text-xl font-bold mb-4"),
                    Div(
                        Div(f"Total Connections: {sse_stats['total_connections']}", cls="mb-2"),
                        Div(f"Active Connections: {sse_stats['active_connections']}", cls="mb-2"),
                        Div(f"Sessions with Connections: {sse_stats['connections_by_session']}", cls="mb-2"),
                        Div(f"Users with Connections: {sse_stats['connections_by_user']}", cls="mb-2"),
                        Div(f"Subscribed State Types: {sse_stats['subscribed_states']}", cls="mb-2"),
                        Div(f"Record Subscriptions: {sse_stats['subscribed_records']}", cls="mb-2"),
                        cls="bg-blue-50 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # State Registry Stats
                Div(
                    H2("State Registry Statistics", cls="text-xl font-bold mb-4"),
                    Div(
                        Div(f"Registered State Types: {len(state_registry._state_configs)}", cls="mb-2"),
                        Div(f"Cached State Instances: {cached_states}", cls="mb-2"),
                        Div("Registered Types:", cls="mb-2 font-bold"),
                        *[
                            Div(f"  • {state_cls.__name__} ({config.scope.value} scope, persist: {config.auto_persist})", 
                                cls="ml-4 text-sm text-gray-600")
                            for state_cls, config in state_registry._state_configs.items()
                        ],
                        cls="bg-green-50 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Persistence Backend Status
                Div(
                    H2("Persistence Backends", cls="text-xl font-bold mb-4"),
                    Div(
                        Div(f"Available Backends: {len(persistence_manager.backends)}", cls="mb-2"),
                        Div("Backend Types:", cls="mb-2 font-bold"),
                        *[
                            Div(f"  • {name} ({type(backend).__name__})", 
                                cls="ml-4 text-sm text-gray-600")
                            for name, backend in persistence_manager.backends.items()
                        ],
                        cls="bg-purple-50 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # System Information
                Div(
                    H2("System Information", cls="text-xl font-bold mb-4"),
                    Div(
                        Div(f"Session ID: {req.cookies.get('session_', 'auto-generated')[:100]}", cls="mb-2 font-mono text-sm"),
                        Div(f"Authentication: {auth or 'Not authenticated'}", cls="mb-2 font-mono text-sm"),
                        Div(f"FastState Version: Enhanced with SSE + Persistence", cls="mb-2 font-mono text-sm"),
                        cls="bg-gray-50 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Test SSE Connection
                Div(
                    H2("Test SSE Connection", cls="text-xl font-bold mb-4"),
                    Div(
                        Button("Connect to Global SSE", 
                               onclick="connectToSSE()",
                               cls="bg-blue-500 text-white px-4 py-2 rounded mr-2"),
                        Button("Disconnect SSE", 
                               onclick="disconnectSSE()",
                               cls="bg-red-500 text-white px-4 py-2 rounded"),
                        Div(id="sse-status", cls="mt-4 p-3 rounded bg-gray-100"),
                        cls="mb-6"
                    ),
                    
                    Script("""
                        let eventSource = null;
                        
                        function connectToSSE() {
                            if (eventSource) {
                                eventSource.close();
                            }
                            
                            eventSource = new EventSource('/faststate/sse?states=CounterState,ChatState');
                            document.getElementById('sse-status').innerHTML = 'Connecting to SSE...';
                            
                            eventSource.onopen = function() {
                                document.getElementById('sse-status').innerHTML = 
                                    '<span class="text-green-600">✅ Connected to SSE stream</span>';
                            };
                            
                            eventSource.onmessage = function(event) {
                                const status = document.getElementById('sse-status');
                                status.innerHTML = 
                                    '<span class="text-blue-600">📡 Received: </span>' + 
                                    '<code class="text-sm">' + event.data.substring(0, 100) + '...</code>';
                            };
                            
                            eventSource.onerror = function() {
                                document.getElementById('sse-status').innerHTML = 
                                    '<span class="text-red-600">❌ SSE connection error</span>';
                            };
                        }
                        
                        function disconnectSSE() {
                            if (eventSource) {
                                eventSource.close();
                                eventSource = null;
                                document.getElementById('sse-status').innerHTML = 
                                    '<span class="text-gray-600">Disconnected from SSE</span>';
                            }
                        }
                    """),
                    cls="mb-6"
                ),
                
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-4xl"
            )
        )
    )


@rt('/login')
def login_demo(req: Request, sess: dict):
    """
    Mock login page to demonstrate authentication flow.
    """
    return Titled("Login Demo",
        Main(
            Div(
                H1("🔒 Login Demo", cls="text-3xl font-bold mb-6"),
                
                P("This is a demo of the authentication system. In a real app, you would integrate with your actual auth system.", 
                  cls="text-gray-600 mb-6"),
                
                Div(
                    H3("Quick Auth Examples", cls="text-lg font-bold mb-4"),
                    P("Click these links to simulate different authentication states:", cls="mb-4"),
                    
                    Div(
                        A("Login as Regular User", href="/auth-demo?user=john&permissions=", 
                          cls="bg-blue-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                        A("Login as Admin", href="/auth-demo?user=admin&permissions=admin,product.edit,inventory.manage", 
                          cls="bg-red-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                        A("Login as Product Manager", href="/auth-demo?user=manager&permissions=product.edit,product.view", 
                          cls="bg-green-500 text-white px-4 py-2 rounded mb-2 inline-block"),
                        cls="mb-6"
                    ),
                    
                    cls="mb-6"
                ),
                
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-2xl"
            )
        )
    )


@rt('/auth-demo')
def auth_demo(req: Request, sess: dict, user: str = "", permissions: str = ""):
    """
    Demo authentication handler - sets up mock auth in session.
    """
    if user:
        # Set mock authentication in session
        req.session['auth'] = user
        req.session[f'user_permissions_{user}'] = permissions.split(',') if permissions else []
        req.session[f'user_roles_{user}'] = ['admin'] if 'admin' in permissions else ['user']
        
        return RedirectResponse("/", status_code=302)
    else:
        # Clear auth
        sess.pop('auth', None)
        return RedirectResponse("/", status_code=302)


# =============================================================================
# BACKWARD COMPATIBILITY ROUTES
# =============================================================================

# Include original routes for backward compatibility
old_routes.to_app(app)
state_rt.to_app(app)

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎉 FastState Demo Application Starting!")
    print("="*60)
    
    serve(reload=True)