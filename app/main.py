from fasthtml.common import *
from monsterui.all import *
from faststate import *
from route_collector import add_routes

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
    ],
)

custom_theme_css = Link(rel="stylesheet", href="/css/custom_theme.css", type="text/css")
monsterui_headers = Theme.claude.headers()

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

add_routes(app)
# Import and add state routes
states_rt.to_app(app)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎉 FastState Demo Application Starting!")
    print("="*60)
    
    serve(reload=True)