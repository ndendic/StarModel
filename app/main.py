from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from route_collector import add_routes

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

custom_theme_css = Link(rel="stylesheet", href="/css/custom_theme.css", type="text/css")
favicon_link = Link(rel="icon", href="/favicon.svg", type="image/svg+xml")
monsterui_headers = Theme.zinc.headers(highlightjs=True, apex_charts=True, radii=ThemeRadii.md)

app, rt = fast_app(
    static_path="assets",
    live=True,
    pico=False,
    htmx=True,
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
# Import and add entity routes
entities_rt.to_app(app)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎉 StarModel Demo Application Starting!")
    print("="*60)
    
    serve(reload=True)