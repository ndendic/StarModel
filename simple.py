import asyncio
from starmodel import *
from fasthtml.common import *
from monsterui.all import *

custom_theme_css = Link(rel="stylesheet", href="app/assets/css/custom_theme.css", type="text/css")

app, rt = fast_app(
    htmx=False,
    hdrs=(
        Theme.zinc.headers(radii=ThemeRadii.md),
        datastar_script,
        custom_theme_css,
    ),
    htmlkw=dict(cls="bg-surface-light uk-theme-claude dark:bg-surface-dark bg-background font-sans antialiased"),
)

class Counter(State):
    count: int = 0
    update_count: int = 0
    
    @event
    def increment(self, amount: int = 1):
        self.count += amount
        self.update_count += 1

    @event
    def decrement(self, amount: int = 1):
        self.count -= amount
        self.update_count += 1

    @event
    async def reset(self):
        while self.count > 0:
            self.count -= 1
            yield self.count
            await asyncio.sleep(0.04)
        self.count = 0
        self.update_count += 1

@rt
def index(req: Request):
    counter = Counter.get(req)
    return Main(
        counter,
        H1("🔢 Counter Demo"),
        # Counter display
        Card(
            Div(
                Span(data_text=Counter.Scount, cls=TextT.primary + "text-7xl font-bold"),
                cls="text-center mb-2"
            ),
            Div("Total updates: ", Span(data_text=Counter.Supdate_count), cls=TextT.primary),
            cls=CardT.default + "text-center my-6",
        ),            
        # Counter controls
        Div(
            Div(
                Button("-100",data_on_click=Counter.decrement(100), cls=ButtonT.secondary),
                Button("-10", data_on_click=Counter.decrement(10), cls=ButtonT.secondary),
                Button("-1", data_on_click=Counter.decrement(1), cls=ButtonT.secondary),
                Button("Reset", data_on_click=Counter.reset(), cls=ButtonT.secondary),
                Button("+1", data_on_click=Counter.increment(1), cls=ButtonT.secondary),
                Button("+10", data_on_click=Counter.increment(10), cls=ButtonT.secondary),
                Button("+100", data_on_click=Counter.increment(100), cls=ButtonT.secondary),
                cls="text-center mb-6 flex gap-2 justify-center"
            ),
            cls="mb-6"
        ),
        # Custom increment
        Div(
            Form(
                Input(name="amount", type="number", value="1", data_bind="$amount",cls="w-24"),
                Button("+", type="submit", cls=ButtonT.secondary),
                data_on_submit=Counter.increment(),
                cls="mb-6"
            ),
            cls="text-center mb-6"
        ),
        cls="container mx-auto p-8 max-w-3xl"
    )

# Import and add state routes
states_rt.to_app(app)

if __name__ == "__main__":
    serve(reload=True, port=8080)