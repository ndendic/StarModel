from fasthtml.common import *
from monsterui.all import *
from faststate import *
import json

rt = APIRouter()

class UserProfileState(State):
    """User-scoped state - persists across sessions for authenticated users."""
    name: str = ""
    email: str = ""
    preferences: dict = {}
    
    # Auto-registration configuration
    _config = StateConfig(
        scope=StateScope.USER,
        auto_persist=True,
        persistence_backend="database",
        ttl=3600
    )
    
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