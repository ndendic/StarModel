import asyncio
from contextlib import asynccontextmanager
from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from starmodel.persistence import MemoryRepo
from route_collector import add_routes

# from starmodel import UnitOfWork, InProcessBus, persistence_manager, register_entities, register_all_entities
from starmodel import  register_all_entities
# Import all entities
# from entities.landing import Landing
# from pages.counter import Counter  
# from pages.dashboard import Dashboard
# from pages.data_playground import DataPlaygroundEntity


def auth_beforeware(req, sess):
    """
    Simple authentication beforeware using FastHTML/Starlette pattern.
    This demonstrates how to handle auth outside of StarModel.
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

async def periodic_cleanup():
    """Background task to clean up expired entities every 5 minutes."""
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            cleaned = MemoryRepo().cleanup_expired_sync()
            if cleaned > 0:
                print(f"Cleaned up {cleaned} expired entities")
        except Exception as e:
            print(f"Error during cleanup: {e}")

@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager for background tasks."""
    # Start cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    print("Background TTL cleanup task started")
    yield
    # Cleanup on shutdown
    cleanup_task.cancel()
    print("Background TTL cleanup task stopped")

custom_theme_css = Link(rel="stylesheet", href="/css/custom_theme.css", type="text/css")
favicon_link = Link(rel="icon", href="/favicon.svg", type="image/svg+xml")
monsterui_headers = Theme.zinc.headers(highlightjs=True, apex_charts=True, radii=ThemeRadii.md)

app, rt = fast_app(
    static_path="assets",
    live=True,
    pico=False,
    htmx=True,
    lifespan=lifespan,  # Add lifespan for background tasks
    # before=beforeware,  # Add auth beforeware
    hdrs=(
        # HighlightJS(langs=["python", "html"]),
        Link(rel='preconnect', href='https://fonts.googleapis.com'),
        Link(rel='preconnect', href='https://fonts.gstatic.com', crossorigin=''),
        Link(href='https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&family=Geist+Mono:wght@100..900&family=Geist:wght@100..900&family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap', rel='stylesheet'),
        Link(href='https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&display=swap', rel='stylesheet'),
        monsterui_headers,
        custom_theme_css,
        Link(rel="stylesheet", href='https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-light.css', id='hljs-light'),
        Link(rel="stylesheet", href='https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.css', id='hljs-dark'),
        # Link(rel="stylesheet", href='https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/srcery.css', id='hljs-light'),
        favicon_link,
        datastar_script,
    ),
    htmlkw=dict(cls="bg-surface-light uk-theme-claude dark:bg-surface-dark bg-background font-sans antialiased"),
)

add_routes(app)

# Import and register entity routes using new application service layer


# # Create application service layer components
# bus = InProcessBus()
# uow = UnitOfWork(persistence_manager, bus)

# # Register entities with FastHTML adapter
# entity_classes = [Landing, Counter, Dashboard, DataPlaygroundEntity]
# register_entities(rt, entity_classes, uow)

register_all_entities(rt)
# # Keep old route registration for backward compatibility
# entities_rt.to_app(app)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎉 StarModel Demo Application Starting!")
    print("="*60)
    
    serve(reload=True)