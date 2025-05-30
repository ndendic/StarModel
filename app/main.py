

from fasthtml.common import *
from monsterui.all import *
from routes import rt as routes

# from route_collector import add_routes

custom_theme_css = Link(rel="stylesheet", href="/css/custom_theme.css", type="text/css")
monsterui_headers = Theme.rose.headers()
datastar_script = Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0-beta.11/bundles/datastar.js", type="module")


app, rt = fast_app(
    static_path="assets",
    live=True,
    pico=False,
    hdrs=(
        monsterui_headers,
        custom_theme_css,
        datastar_script,
    ),
    htmlkw=dict(cls="bg-surface-light dark:bg-surface-dark bg-background font-sans antialiased"),
)
routes.to_app(app)

if __name__ == "__main__":
    serve(reload=True)
