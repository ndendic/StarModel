"""
FastState Demo Application

This application demonstrates the complete FastState system with automatic
dependency injection, authentication, and different state scopes.
"""

import json
from fasthtml.common import *
from monsterui.all import *

# Import FastState components
from faststate import (
    ReactiveState, event, StateScope, StateConfig, state_registry,
    initialize_faststate, requires_auth
)

# Import existing routes and state routes for backward compatibility
from routes import rt as old_routes
from faststate.state import rt as state_rt

# Initialize FastState integration with FastHTML
print("🚀 Initializing FastState...")
initialize_faststate()

# =============================================================================
# STATE DEFINITIONS WITH DIFFERENT SCOPES
# =============================================================================

class MyState(ReactiveState):
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


class UserProfileState(ReactiveState):
    """User-scoped state - persists across sessions for authenticated users."""
    name: str = ""
    email: str = ""
    preferences: dict = {}
    
    @event
    @requires_auth()
    def update_profile(self, name: str, email: str):
        self.name = name
        self.email = email
        return Div("Profile updated successfully!", cls="text-green-600 font-bold")
    
    @event
    @requires_auth()
    def set_preference(self, key: str, value: str):
        if not isinstance(self.preferences, dict):
            self.preferences = {}
        self.preferences[key] = value
        return Div(f"Preference {key} set to {value}", cls="text-blue-600")


class GlobalSettingsState(ReactiveState):
    """Global state - shared across all users (admin only)."""
    theme: str = "light"
    maintenance_mode: bool = False
    announcement: str = ""
    
    @event
    @requires_auth(permissions=['admin'])
    def toggle_maintenance(self):
        self.maintenance_mode = not self.maintenance_mode
        status = "enabled" if self.maintenance_mode else "disabled"
        return Div(f"Maintenance mode {status}!", cls="text-orange-600 font-bold")
    
    @event
    @requires_auth(permissions=['admin'])
    def set_announcement(self, message: str):
        self.announcement = message
        return Div("Announcement updated!", cls="text-blue-600 font-bold")
    
    @event
    @requires_auth(permissions=['admin'])
    def change_theme(self, theme: str):
        self.theme = theme
        return Div(f"Theme changed to {theme}!", cls="text-purple-600 font-bold")


class ProductState(ReactiveState):
    """Record-scoped state - tied to specific product records."""
    name: str = ""
    price: float = 0.0
    description: str = ""
    in_stock: bool = True
    
    @event
    @requires_auth(permissions=['product.edit'])
    def update_product(self, name: str, price: float, description: str):
        self.name = name
        self.price = price
        self.description = description
        return Div("Product updated!", cls="text-green-600 font-bold")
    
    @event
    @requires_auth(permissions=['inventory.manage'])
    def toggle_stock(self):
        self.in_stock = not self.in_stock
        status = "in stock" if self.in_stock else "out of stock"
        return Div(f"Product marked as {status}!", cls="text-blue-600 font-bold")


# =============================================================================
# STATE REGISTRATION
# =============================================================================

print("📝 Registering state types...")

# Register MyState with session scope (default behavior)
state_registry.register(
    MyState,
    StateConfig(scope=StateScope.SESSION)
)

# Register UserProfileState with user scope (requires authentication)
state_registry.register(
    UserProfileState,
    StateConfig(scope=StateScope.USER, requires_auth=True)
)

# Register GlobalSettingsState with global scope and admin permissions
state_registry.register(
    GlobalSettingsState,
    StateConfig(
        scope=StateScope.GLOBAL, 
        requires_auth=True,
        permissions=['admin']
    )
)

# Register ProductState with record scope for specific products
state_registry.register(
    ProductState,
    StateConfig(
        scope=StateScope.RECORD, 
        requires_auth=True,
        permissions=['product.view'],
        auto_persist=True
    )
)

print("✅ State registration complete!")

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
def index(req: Request, sess: dict, auth: str = None, my_state: MyState = None):
    """
    Main page demonstrating session-scoped state with automatic injection.
    No more manual _get_state() calls needed!
    """
    # Fallback if state injection failed
    if my_state is None:
        from faststate.state import _get_state
        my_state = _get_state(MyState, req, sess)
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
                    Div(f"Session ID: {sess.get('session_id', 'auto-generated')}", cls="font-mono text-sm"),
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
                    A("👤 User Profile", href="/profile", cls="bg-blue-500 text-white px-4 py-2 rounded mr-2 inline-block"),
                    A("⚙️ Admin Panel", href="/admin", cls="bg-purple-500 text-white px-4 py-2 rounded mr-2 inline-block"),
                    A("📦 Product Demo", href="/product/123", cls="bg-green-500 text-white px-4 py-2 rounded mr-2 inline-block"),
                    A("🔒 Login Demo", href="/login", cls="bg-gray-500 text-white px-4 py-2 rounded inline-block"),
                ),
                cls="mb-8"
            ),
            
            cls="container mx-auto p-8 max-w-4xl"
        )
    )


@rt('/profile')
def profile(req: Request, sess: dict, auth: str = None, profile: UserProfileState = None):
    """
    User profile page with user-scoped state.
    Automatically handles authentication requirements.
    """
    # Fallback if state injection failed
    if profile is None:
        from faststate.state import _get_state
        try:
            profile = _get_state(UserProfileState, req, sess)
        except Exception as e:
            return Div(
                P(f"Authentication required: {str(e)}", cls="error text-red-500 font-bold"),
                P(A("Login here", href="/login"), cls="text-blue-500"),
                cls="p-4 bg-red-50 border border-red-200 rounded"
            )
    
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
                    cls="mb-6"
                ),
                
                # Profile form
                Div(
                    H3("Update Profile", cls="text-lg font-bold mb-4"),
                    Form(
                        Input(value=profile.name, name="name", placeholder="Full Name", 
                              cls="border rounded px-3 py-2 mb-3 w-full"),
                        Input(value=profile.email, name="email", placeholder="Email Address", 
                              cls="border rounded px-3 py-2 mb-3 w-full"),
                        Button("Update Profile", type="submit", 
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
def admin_panel(req: Request, sess: dict, auth: str = None, settings: GlobalSettingsState = None):
    """
    Admin panel with global state.
    Automatically enforces admin permissions via state registry.
    """
    # Fallback if state injection failed
    if settings is None:
        from faststate.state import _get_state
        try:
            settings = _get_state(GlobalSettingsState, req, sess)
        except Exception as e:
            return Div(
                P(f"Admin access required: {str(e)}", cls="error text-red-500 font-bold"),
                P(A("Login as admin", href="/login"), cls="text-blue-500"),
                cls="p-4 bg-red-50 border border-red-200 rounded"
            )
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
def product_detail(req: Request, sess: dict, auth: str = None, product: ProductState = None, record_id: int = None):
    """
    Product detail page with record-scoped state.
    Demonstrates state tied to specific database records.
    """
    # Fallback if state injection failed
    if product is None:
        from faststate.state import _get_state
        try:
            product = _get_state(ProductState, req, sess, record_id=record_id)
        except Exception as e:
            return Div(
                P(f"Product access required: {str(e)}", cls="error text-red-500 font-bold"),
                P(A("Login here", href="/login"), cls="text-blue-500"),
                cls="p-4 bg-red-50 border border-red-200 rounded"
            )
    
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
        sess['auth'] = user
        sess[f'user_permissions_{user}'] = permissions.split(',') if permissions else []
        sess[f'user_roles_{user}'] = ['admin'] if 'admin' in permissions else ['user']
        
        return RedirectResponse("/", status_code=302)
    else:
        # Clear auth
        sess.pop('auth', None)
        return RedirectResponse("/", status_code=302)


# =============================================================================
# BACKWARD COMPATIBILITY ROUTES
# =============================================================================

# Include original routes for backward compatibility
# old_routes.to_app(app)
state_rt.to_app(app)

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎉 FastState Demo Application Starting!")
    print("="*60)
    print("Features enabled:")
    print("✅ Automatic state dependency injection")
    print("✅ Session, User, Global, and Record-scoped states")
    print("✅ Authentication and authorization")
    print("✅ Real-time state synchronization via SSE")
    print("✅ Backward compatibility with existing routes")
    print("\nVisit http://localhost:5000 to see the demo!")
    print("="*60)
    
    serve(reload=True)