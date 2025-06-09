import json

from fasthtml.common import *
from monsterui.all import *

def ThemeSwitcher():
    return ThemePicker(custom_themes=[
        ("LightSky", "#0099AD"),
        ("Mandarino", "#E74D3C"),
        ("Candy", "#ff99cc"),
        ("Claude", "#d97757"),
        ("Vercel", "#000000")
    ])

def theme_switcher():
    return Div(
    Button(
        UkIcon(icon='palette', uk_cloak=''),
        cls=ButtonT.ghost,
        # cls='uk-icon-button uk-icon-button-small uk-icon-button-outline'
    ),
    Div(
        Div('Customize', cls='uk-card-title uk-margin-medium-bottom'),
        ThemeSwitcher(),
        uk_drop="mode: click; offset: 8",
        cls="uk-card uk-card-body uk-card-default uk-drop uk-width-large",
    ),
    cls='uk-inline'
)


hotkeys = [
    ("Profile", "⇧⌘P", "/user/profile"),
    ("Billing", "⌘B"),
    ("Settings", "⌘S"),
    ("Logout", "", "/auth/logout", False),
]


def NavSpacedLi(t, s=None, href="#", is_content=True):
    return A(
        DivFullySpaced(P(t, cls=(TextT.muted, TextT.sm)), P(s)),
        href=href + "#",
        hx_boost="true" if is_content else "false",
        hx_target="#content",
        hx_swap_oob=True,
    )


def NavCloseLi(t, s=None, href="#", is_content=True):
    return Li(
        A(
            DivFullySpaced(P(t, cls=(TextT.muted, TextT.sm)), P(s)),
            href=href + "#",
            hx_boost="true" if is_content else "false",
            hx_target="#content",
            hx_swap_oob=True,
            cls=ButtonT.ghost,
        )
    )


def Avatar(
    url,
    h=20,  # Height
    w=20,  # Width
):  # Span with Avatar
    return Span(
        cls=f"relative flex h-{h} w-{w} shrink-0 overflow-hidden rounded-full bg-accent"
    )(
        Img(
            cls="h-full w-full object-cover",
            alt="Avatar",
            loading="lazy",
            src=url,
        )
    )


def DropDownNavContainer(
    *li,  # Components
    cls=NavT.primary,  # Additional classes on the nav
    parent=True,  # Whether to use a parent nav
    uk_nav=False,  # True for default collapsible behavior, see https://franken-ui.dev/docs/nav#component-options for more advanced options
    uk_dropdown=True,  # Whether to use a dropdown
    **kwargs,  # Additional args for the nav
) -> FT:  # DropDown nav container
    "A Nav that is part of a DropDown"
    return Div(cls="uk-drop uk-dropdown", uk_dropdown=uk_dropdown)(
        NavContainer(
            *li, cls=("uk-dropdown-nav", cls), uk_nav=uk_nav, parent=parent, **kwargs
        )
    )



def SidebarToggle():
    return Button(
        UkIcon("menu", height=20, width=20),
        cls="block lg:hidden p-2",  # Show on mobile, hide on desktop
        uk_toggle="target: #mobile-sidebar",
        aria_label="Toggle navigation menu",
    )


nav_items = [
    ("Home", "/"),
    ("Dashboard", "/dashboard")
]


def TopNav(request):
    return Header(
        cls="sticky top-0 z-50 w-full border-b border-border px-2 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
        # cls="sticky top-0 z-50 border-b border-border px-2 lg:px-4 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
    )(
        DivFullySpaced(
            DivLAligned(
                DivLAligned(
                    SidebarToggle(),  # Mobile toggle button
                    # Hide navigation items on mobile
                    DivLAligned(
                        *[NavSpacedLi(item[0], href=item[1]) for item in nav_items],
                    ),
                ),
                cls="hidden lg:flex items-center ml-16",  # Hide on mobile, show on desktop
            ),
            DivRAligned(
                DivRAligned(
                    theme_switcher(),
                    # avatar_dropdown(request),
                    cls="space-x-2 mr-4",
                ),
                # cls="hidden lg:block"
            ),
            # Reduce padding on mobile
        )
    )


def MobileDrawer():
    return Div(
        Button(
            UkIcon("menu", height=24, width=24),
            cls=ButtonT.ghost + " md:hidden",
            uk_toggle="target: #mobile-menu",
        ),
        Modal(
            Div(cls="p-6 bg-background")(
                H3("Menu", cls="text-lg font-semibold mb-4"),
                NavContainer(
                    *[
                        Li(
                            A(
                                label,
                                href=url,
                                cls="flex items-center p-2 hover:bg-muted rounded-lg transition-colors",
                            )
                        )
                        for label, url in nav_items
                    ],
                    Li(DividerLine(lwidth=2, y_space=4)),
                    Li(
                        A(
                            "Sign in",
                            href="/auth/login",
                            cls="flex items-center p-2 hover:bg-muted rounded-lg transition-colors",
                        )
                    ),
                    Li(
                        Button(
                            "Get Started",
                            cls=ButtonT.primary + " w-full mt-2",
                            onclick="window.location.href='/pricing'",
                        )
                    ),
                    cls=NavT.primary + " space-y-2",
                ),
            ),
            id="mobile-menu",
        ),
    )


def NewNav(request):
    return Header(
        cls="sticky top-0 z-100 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
    )(
        Div(cls="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16")(
            Div(cls="flex h-full justify-between items-center")(
                Div(cls="flex items-center gap-x-8")(
                    # Mobile menu drawer
                    MobileDrawer(),
                    # Logo
                    A(href="/", cls="flex items-center")(
                        Span("DataHTML", cls="font-bold text-xl")
                    ),
                    # Desktop navigation
                    Nav(cls="hidden md:flex items-center space-x-8")(
                        *[
                            A(
                                label,
                                href=url,
                                cls="text-sm font-medium transition-colors hover:text-foreground/80 text-foreground/60",
                            )
                            for label, url in nav_items
                        ]
                    ),
                ),
                # Desktop CTA buttons
                Div(cls="hidden md:flex items-center space-x-4")(
                    theme_switcher(),
                    Input(placeholder="Search"),
                    # avatar_dropdown(request),
                ),
            )
        )
    )


def Navbar(request):
    return TopNav(request)
