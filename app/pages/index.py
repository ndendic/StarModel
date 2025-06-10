from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from pages.templates import page_template

rt = APIRouter()

class LandingState(State):
    """Interactive landing page showcasing StarModel's reactive magic."""
    live_counter: int = 0
    active_connections: int = 1
    lines_written: int = 42
    deploy_status: str = "Ready"
    demo_code: str = """class TodoState(State):
    items: list = []
    count: int = 0
    
    @event
    def add_item(self, text: str):
        self.items.append(text)
        self.count += 1"""
    
    @event
    def pulse_counter(self):
        self.live_counter += 1
        self.active_connections += 1
        self.lines_written += 2
        
    @event
    def simulate_deploy(self):
        self.deploy_status = "Deploying..." if self.deploy_status == "Ready" else "Ready"

def reactive_hero():
    """Hero section with live code-to-UI demonstration."""
    return Section(       
        # Animated background with subtle pulse
        Div(
            cls="absolute animate-[wiggle_1s_ease-in-out_infinite] inset-0 overflow-hidden",
            style="background: linear-gradient(135deg, hsl(var(--accent)) 0%, hsl(var(--primary)) 100%)"
        ),
        
        Container(
            # Main hero grid - code editor + live result
            Grid(
                # Left: Interactive Code Editor
                Card(
                    # Terminal-style header
                    Div(
                        DivLAligned(
                            Div(
                                Span(cls="w-3 h-3 bg-red-500 rounded-full"),
                                Span(cls="w-3 h-3 bg-yellow-500 rounded-full"), 
                                Span(cls="w-3 h-3 bg-green-500 rounded-full"),
                                cls="flex gap-2"
                            ),
                            Div("main.py", cls="text-sm font-mono text-muted-foreground"),
                            Span("⚡ Live", cls="animate-pulse text-xs bg-primary text-primary-foreground px-2 py-1 rounded"),
                            cls="justify-between w-full"
                        ),
                        cls="px-4 py-3 border-b bg-muted/20"
                    ),
                    
                    # Code content with line numbers
                    Div(
                                
                         render_md("""```python
from starmodel import State, event
from fasthtml.common import *

class CounterState(State):
    count: int = 0
    
    @event 
    def increment(self):
        self.count += 1
        
@rt('/')
def home(req):
    state = CounterState.get(req)
    return Div(
        H1(f"Count: {state.count}"),
        Button("+1", 
               data_on_click=CounterState.increment())
    )
```
"""),
                                                        
                        
                        # Live status indicator
                        Div(
                            DivLAligned(
                                UkIcon("activity", cls="w-4 h-4 text-primary"),
                                Span("Live Updates: ", cls="text-sm text-muted-foreground"),
                                Span(data_text=LandingState.live_counter_signal, 
                                    cls="font-mono font-bold text-primary"),
                                cls="gap-2"
                            ),
                            cls="px-4 py-2 border-t bg-muted/10"
                        ),
                        cls="relative"
                    ),
                    cls="bg-card border shadow-lg overflow-hidden"
                ),
                
                # Right: Live Result Preview
                Card(
                    # Browser-style header
                    Div(
                        DivLAligned(
                            Div(
                                Span(cls="w-3 h-3 bg-gray-400 rounded-full"),
                                Span(cls="w-3 h-3 bg-gray-400 rounded-full"),
                                UkIcon("external-link", cls="w-3 h-3 text-muted-foreground"),
                                cls="flex gap-2"
                            ),
                            Div(
                                Span("localhost:5000", cls="text-sm font-mono text-muted-foreground bg-muted px-2 py-1 rounded"),
                                cls="flex-1 text-center"
                            ),
                            Button("Deploy", 
                                  data_on_click=LandingState.simulate_deploy(),
                                  cls=ButtonT.primary + " text-xs h-7"),
                            cls="justify-between w-full"
                        ),
                        cls="px-4 py-3 border-b bg-background"
                    ),
                    
                    # Live preview content
                    Div(
                        DivCentered(
                            H1("⭐ StarModel Demo", cls="text-3xl font-bold text-primary mb-6"),
                            
                            # Interactive counter matching the code
                            Card(
                                DivCentered(
                                    H2("Count: ", 
                                       Span(data_text=LandingState.live_counter_signal, 
                                           cls="font-mono text-4xl text-primary")),
                                    Button("🚀 +1", 
                                          data_on_click=LandingState.pulse_counter(),
                                          cls=ButtonT.primary + " text-lg mt-4"),
                                    cls="py-8"
                                ),
                                cls="bg-muted/30 border-2 border-dashed border-primary/30"
                            ),
                            
                            # Real-time metrics
                            Grid(
                                Div(
                                    Span(data_text=LandingState.active_connections_signal, 
                                        cls="text-2xl font-bold text-primary"),
                                    P("Active Connections", cls="text-sm text-muted-foreground"),
                                    cls="text-center"
                                ),
                                Div(
                                    Span(data_text=LandingState.lines_written_signal, 
                                        cls="text-2xl font-bold text-primary"),
                                    P("Lines Written", cls="text-sm text-muted-foreground"),
                                    cls="text-center"
                                ),
                                Div(
                                    Span(data_text=LandingState.deploy_status_signal, 
                                        cls="text-sm font-mono text-primary"),
                                    P("Deploy Status", cls="text-sm text-muted-foreground"),
                                    cls="text-center"
                                ),
                                cols=3, gap=4, cls="mt-6"
                            )
                        ),
                        cls="p-6 bg-background min-h-[400px]"
                    ),
                    cls="bg-card border shadow-lg"
                ),
                cols_lg=2, cls="mb-8 gap-x-8"
            ),
            
            # Hero text below the demo
            DivCentered(
                H1("Reactive State Management for Python", 
                   cls="text-5xl font-bold text-foreground mb-4"),
                P("Build interactive web applications entirely in Python. No JavaScript, no build tools, no complexity.",
                  cls="text-xl text-muted-foreground mb-8 max-w-2xl"),
                
                # CTA with live metrics
                DivLAligned(
                    Button("🎯 Start Building", cls=ButtonT.primary + " text-lg px-8 py-3"),
                    Button("📖 View Docs", href="/docs", cls=ButtonT.secondary + "text-lg px-8 py-3"),
                    cls="gap-4"
                )
            ),
            cls="py-12 relative z-10"
        ),
        cls="relative min-h-screen flex items-center"
    )

def developer_showcase():
    """Showcase section targeted at Python developers."""
    return Section(
        Container(
            DivCentered(
                H2("Why Python Developers Love StarModel", 
                   cls="text-4xl font-bold text-foreground mb-4"),
                P("Finally, reactive UIs without leaving Python", 
                  cls="text-xl text-muted-foreground mb-12")
            ),
            
            # Feature cards with developer-focused messaging
            Grid(
                Card(
                    DivCentered(
                        # Terminal icon with pulse animation
                        Div(
                            Span("⚡", cls="text-5xl"),
                            cls="mb-4 animate-pulse"
                        ),
                        H3("Real-time Magic", cls="text-xl font-bold text-foreground mb-4"),
                        P("Watch your UI update instantly as state changes. No manual DOM manipulation, no useEffect hell.",
                          cls="text-muted-foreground mb-6"),
                        
                        # Live demo mini-widget
                        Div(
                            P("Live Updates: ", 
                              Span(data_text=LandingState.live_counter_signal, 
                                  cls="font-mono font-bold text-primary")),
                            cls="bg-muted p-3 rounded font-mono text-sm"
                        )
                    ),
                    cls="h-full"
                ),
                
                Card(
                    DivCentered(
                        Div(
                            Span("🐍", cls="text-5xl"),
                            cls="mb-4"
                        ),
                        H3("Pure Python", cls="text-xl font-bold text-foreground mb-4"),
                        P("From data models to UI components, everything stays in Python. Your favorite language, all the way down.",
                          cls="text-muted-foreground mb-6"),
                        
                        # Code snippet
                        Pre(
                            Code(
                                """@event
def handle_click(self):
    self.clicked = True
    # UI updates automatically!""",
                                cls="language-python text-xs bg-muted p-3 rounded"
                            )
                        )
                    ),
                    cls="h-full"
                ),
                
                Card(
                    DivCentered(
                        Div(
                            Span("🚀", cls="text-5xl"),
                            cls="mb-4"
                        ),
                        H3("Zero Setup", cls="text-xl font-bold text-foreground mb-4"),
                        P("No webpack, no babel, no package.json. Just install StarModel and start building reactive apps.",
                          cls="text-muted-foreground mb-6"),
                        
                        # Terminal command
                        Div(
                            Code("pip install starmodel", 
                                 cls="font-mono text-sm bg-primary text-primary-foreground px-3 py-2 rounded"),
                            P("That's it. You're ready to build.", 
                              cls="text-xs text-muted-foreground mt-2")
                        )
                    ),
                    cls="h-full"
                ),
                cols_lg=3, gap=6
            )
        ),
        cls="py-20 bg-muted/20"
    )

def interactive_playground():
    """Interactive code playground section."""
    return Section(
        Container(
            DivCentered(
                H2("See It In Action", cls="text-4xl font-bold text-foreground mb-4"),
                P("Modify the code below and watch the magic happen", 
                  cls="text-xl text-muted-foreground mb-12")
            ),
            
            # Split view playground
            Grid(
                # Code editor
                Card(
                    Div(
                        H3("✨ Interactive Code", cls="text-lg font-bold text-foreground mb-4"),
                        
                        # Editable code area (simplified for demo)
                        Div(
                            Pre(
                                Code(
                                    """class DemoState(State):
    message: str = "Hello StarModel!"
    clicks: int = 0
    
    @event
    def update_message(self, msg: str):
        self.message = msg
        
    @event  
    def increment(self):
        self.clicks += 1""",
                                    cls="language-python text-sm leading-relaxed"
                                )
                            ),
                            cls="bg-muted/30 p-4 rounded border-2 border-dashed border-primary/30"
                        ),
                        
                        # Action buttons
                        DivLAligned(
                            Button("🔄 Run Code", 
                                  data_on_click=LandingState.pulse_counter(),
                                  cls=ButtonT.primary + " text-sm"),
                            Button("📋 Copy", cls=ButtonT.ghost + " text-sm"),
                            cls="gap-2 mt-4"
                        )
                    ),
                    cls="h-full"
                ),
                
                # Live result
                Card(
                    Div(
                        H3("⚡ Live Result", cls="text-lg font-bold text-foreground mb-4"),
                        
                        # Simulated UI output
                        Div(
                            Card(
                                H4("StarModel Demo App", cls="text-lg font-bold mb-4"),
                                P("Message: Hello StarModel!", cls="mb-4"),
                                P("Clicks: ", 
                                  Span(data_text=LandingState.live_counter_signal, 
                                      cls="font-mono font-bold text-primary")),
                                Button("Click Me!", 
                                      data_on_click=LandingState.pulse_counter(),
                                      cls=ButtonT.primary),
                                cls="bg-background p-4"
                            ),
                            cls="border-2 border-dashed border-primary/30 p-4 rounded"
                        ),
                        
                        # Status
                        Div(
                            DivLAligned(
                                UkIcon("zap", cls="w-4 h-4 text-primary"),
                                Span("Live Connection Active", cls="text-sm text-primary"),
                                cls="gap-2"
                            ),
                            cls="mt-4"
                        )
                    ),
                    cls="h-full"
                ),
                cols_lg=2, gap=6
            )
        ),
        cls="py-20"
    )

def developer_cta():
    """Strong CTA section for developers."""
    return Section(
        Container(
            DivCentered(
                H2("Ready to Build Something Amazing?", 
                   cls="text-4xl font-bold text-primary-foreground mb-6"),
                P("Join Python developers who are building the future of reactive web apps", 
                  cls="text-xl text-primary-foreground/80 mb-8"),
                
                # Two-step CTA
                Grid(
                    Card(
                        H3("🚀 Quick Start", cls="text-xl font-bold text-foreground mb-4"),
                        P("Get up and running in under 2 minutes", cls="text-muted-foreground mb-6"),
                        
                        # Terminal-style install
                        Div(
                            Div(
                                Span("$", cls="text-primary mr-2"),
                                Span("pip install starmodel", cls="font-mono"),
                                cls="bg-muted p-3 rounded mb-2 font-mono text-sm"
                            ),
                            Div(
                                Span("$", cls="text-primary mr-2"),
                                Span("python -m starmodel init", cls="font-mono"),
                                cls="bg-muted p-3 rounded mb-4 font-mono text-sm"
                            ),
                            Button("Copy Commands", cls=ButtonT.primary + " w-full")
                        )
                    ),
                    
                    Card(
                        H3("📚 Learn More", cls="text-xl font-bold text-foreground mb-4"),
                        P("Explore examples and documentation", cls="text-muted-foreground mb-6"),
                        
                        DivLAligned(
                            A("📖 Documentation", href="/docs", cls=ButtonT.primary),
                            A("🎮 Examples", href="/demo", cls=ButtonT.ghost),
                            cls="gap-4 flex-col w-full"
                        )
                    ),
                    cols_lg=2, gap=6, cls="max-w-4xl"
                )
            )
        ),
        cls="py-20 bg-primary text-primary-foreground"
    )

@rt('/')
@page_template(title="⭐ StarModel - Reactive State Management for Python")
def index(req: Request):
    """Revolutionary landing page showcasing StarModel's reactive magic."""
    state = LandingState.get(req)
    
    return Main(
        state,
        reactive_hero(),
        developer_showcase(), 
        interactive_playground(),
        developer_cta(),
        cls="min-h-screen"
    )

@rt('/demo')
@page_template(title="StarModel Live Demo")
def demo(req: Request):
    """Enhanced interactive demo playground."""
    state = LandingState.get(req)
    
    return Main(
        state,
        Container(
        DivCentered(
            H1("🧪 StarModel Interactive Playground", 
               cls="text-4xl font-bold text-foreground mb-4"),
            P("Experience real-time state management in action", 
              cls="text-muted-foreground mb-8")
        ),
        
        Grid(
            Card(
                H3("Live Counter Demo", cls="text-xl font-bold text-foreground mb-4"),
                DivCentered(
                    P("Current Value:", cls="text-muted-foreground"),
                    Span(data_text=LandingState.live_counter_signal, 
                        cls="text-4xl font-mono font-bold text-primary block my-4"),
                    DivLAligned(
                        Button("−", data_on_click=LandingState.pulse_counter(-1), 
                              cls=ButtonT.secondary + " w-12"),
                        Button("Reset", data_on_click=LandingState.pulse_counter(0), 
                              cls=ButtonT.ghost),
                        Button("+", data_on_click=LandingState.pulse_counter(), 
                              cls=ButtonT.primary + " w-12"),
                        cls="gap-3"
                    )
                )
            ),
            
            Card(
                H3("Real-time Metrics", cls="text-xl font-bold text-foreground mb-4"),
                Grid(
                    Div(
                        P("Live Updates", cls="text-muted-foreground text-sm"),
                        Span(data_text=LandingState.live_counter_signal, 
                            cls="text-2xl font-bold text-primary")
                    ),
                    Div(
                        P("Connections", cls="text-muted-foreground text-sm"),
                        Span(data_text=LandingState.active_connections_signal, 
                            cls="text-2xl font-bold text-primary")
                    ),
                    cols=2, gap=4
                )
            ),
            cols_lg=2, gap=6, cls="mb-8"
        ),
        
        DivCentered(
            DivLAligned(
                A("← Back to Home", href="/", cls=ButtonT.ghost),
                A("📊 Dashboard", href="/dashboard", cls=ButtonT.primary),
                cls="gap-4"
            )
        ),
        cls="py-8"
        )
    )