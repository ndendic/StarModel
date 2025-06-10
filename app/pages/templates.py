from fasthtml.common import *
from monsterui.franken import *

from pages.components.navbar import TopNav, Navbar
from pages.components.sidebar import Sidebar
from datastar_py.fasthtml import DatastarResponse, ServerSentEventGenerator

def is_ds(request=None):
    "Check if the request is an HTMX request"
    return request and ("datastar" in request.headers or "datastar" in request.query_params)

def site_page(title, content):
    return Title(title), Body(
        Navbar(),
        Main(cls="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12")(
            Div(cls="grid grid-cols-1 md:grid-cols-3 gap-8")(
                content, cls="min-h-screen"
            ),
        ),
    )

def page_template(title="StarModel"):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            content = func(request)
            if is_ds(request):
                return content
            return site_page(title, content)
        return wrapper
    return decorator


def app_page(title, request, content):
    return Title(title), Body(
        TopNav(request),
        Div(cls="flex")(
            Sidebar(request),
            Main(
                cls="w-3/4 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4",
            )(
                Div(cls="grid grid-cols-1 md:grid-cols-3 gap-8", id="content")(
                    content,
                    cls="min-h-screen",
                )
            ),
        ),
    )


def app_template(title="App"):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            content = func(request)
            if is_ds(request):
                return DatastarResponse(ServerSentEventGenerator.merge_fragments(content, selector="#content"))
            return app_page(title, request, content)

        return wrapper

    return decorator


