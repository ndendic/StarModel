from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from pages.templates import page_template
import random

rt = APIRouter()

class LandingState(State):
    """Premium interactive landing page showcasing StarModel's revolutionary capabilities."""
    live_counter: int = 0
    active_connections: int = 847
    lines_written: int = 50281
    deploy_status: str = "✅ Production"
    github_stars: int = 1247
    npm_downloads: str = "12.4k/week"
    response_time: str = "<1ms"
    code_completion: int = 0
    demo_message: str = "Hello, StarModel!"
    performance_score: int = 99
    
    @event
    def pulse_counter(self, amount: int = 1):
        if amount == 0:
            self.live_counter = 0
        elif amount == -1:
            self.live_counter = max(0, self.live_counter - 1)
        else:
            self.live_counter += amount
        self.active_connections += random.randint(1, 3)
        self.lines_written += random.randint(5, 25)
        
    @event
    def simulate_deploy(self):
        statuses = ["🚀 Deploying...", "✅ Production", "⚡ Building", "🔄 Updating"]
        current_idx = statuses.index(self.deploy_status) if self.deploy_status in statuses else 0
        self.deploy_status = statuses[(current_idx + 1) % len(statuses)]
        
    @event
    def update_demo_message(self, msg: str):
        self.demo_message = msg
        
    @event 
    def simulate_typing(self):
        self.code_completion = min(100, self.code_completion + 10)
        
    @event
    def boost_performance(self):
        self.performance_score = random.randint(95, 100)
        self.response_time = f"<{random.randint(1,3)}ms"

def premium_hero():
    """Revolutionary hero section with interactive code playground and real-time preview."""
    return Section(       
        # Premium animated gradient background
        Div(
            cls="absolute inset-0 overflow-hidden",
            style="""
                background: linear-gradient(135deg, 
                    rgba(99, 102, 241, 0.1) 0%, 
                    rgba(168, 85, 247, 0.1) 25%,
                    rgba(236, 72, 153, 0.1) 50%,
                    rgba(251, 146, 60, 0.1) 75%,
                    rgba(34, 197, 94, 0.1) 100%);
                animation: gradient-shift 20s ease infinite;
            """
        ),
        
        # Floating particles effect
        Div(
            *[Div(cls=f"absolute w-1 h-1 bg-primary/20 rounded-full animate-float",
                 style=f"left: {i*13}%; top: {i*7}%; animation-delay: {i*0.5}s;") 
              for i in range(15)],
            cls="absolute inset-0 pointer-events-none"
        ),
        
        Container(
            # Hero content with elevated design
            DivCentered(
                # Main headline with gradient text
                Div(
                    H1(
                        "Reactive State Management",
                        Br(),
                        Span("Redefined", cls="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent"),
                        cls="text-6xl md:text-7xl font-bold text-center leading-tight mb-6"
                    ),
                    P(
                        "Build ",
                        Strong("interactive web applications", cls="text-primary"),
                        " entirely in Python. Zero JavaScript, zero complexity, infinite possibilities.",
                        cls="text-xl md:text-2xl text-muted-foreground text-center max-w-4xl mb-12 leading-relaxed"
                    ),
                    cls="mb-16"
                ),
                
                # Interactive demo section
                Grid(
                    # Code Editor with premium styling
                    Card(
                        # Premium terminal header with glass effect
                        Div(
                            DivLAligned(
                                Div(
                                    Span(cls="w-3 h-3 bg-red-500 rounded-full shadow-lg"),
                                    Span(cls="w-3 h-3 bg-yellow-500 rounded-full shadow-lg"), 
                                    Span(cls="w-3 h-3 bg-green-500 rounded-full shadow-lg"),
                                    cls="flex gap-2"
                                ),
                                Div(
                                    UkIcon("code", cls="w-4 h-4 mr-2 text-primary"),
                                    Span("starmodel_demo.py", cls="text-sm font-mono text-foreground font-medium"),
                                    cls="flex items-center"
                                ),
                                Div(
                                    Span("⚡", cls="mr-1"),
                                    Span("LIVE", cls="text-xs font-bold"),
                                    cls="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-3 py-1 rounded-full text-xs animate-pulse shadow-lg"
                                ),
                                cls="justify-between w-full"
                            ),
                            cls="px-6 py-4 border-b bg-gradient-to-r from-background/50 to-muted/50 backdrop-blur-sm"
                        ),
                    
                        # Enhanced code content with syntax highlighting
                        Div(
                            # Code block with premium styling
                            Pre(
                                Code(
                                    """from starmodel import State, event
from fasthtml.common import *

class DemoState(State):
    message: str = "Hello, StarModel!"
    count: int = 0
    status: str = "Ready"
    
    @event
    def update_message(self, msg: str):
        self.message = msg
        
    @event
    def increment(self):
        self.count += 1
        self.status = "Updated!"
        
@rt('/demo')
def demo_page(req):
    state = DemoState.get(req)
    return Main(
        state,  # Auto-sync state
        Card(
            H2(data_text=DemoState.message_signal),
            P(f"Count: {state.count}"),
            Button("Click Me!", 
                   data_on_click=DemoState.increment())
        )
    )""",
                                    cls="language-python text-sm leading-relaxed font-mono"
                                ),
                                cls="bg-gradient-to-br from-slate-900 to-slate-800 text-slate-100 p-6 rounded-lg overflow-x-auto border border-slate-700 shadow-2xl"
                            ),
                                                        
                        
                            # Real-time metrics with glassmorphism
                            Div(
                                Grid(
                                    Div(
                                        DivLAligned(
                                            UkIcon("zap", cls="w-4 h-4 text-green-500"),
                                            Span("Updates: ", cls="text-sm text-muted-foreground"),
                                            Span(data_text=LandingState.live_counter_signal, 
                                                cls="font-mono font-bold text-green-500"),
                                            cls="gap-2"
                                        )
                                    ),
                                    Div(
                                        DivLAligned(
                                            UkIcon("users", cls="w-4 h-4 text-blue-500"),
                                            Span("Active: ", cls="text-sm text-muted-foreground"),
                                            Span(data_text=LandingState.active_connections_signal, 
                                                cls="font-mono font-bold text-blue-500"),
                                            cls="gap-2"
                                        )
                                    ),
                                    Div(
                                        DivLAligned(
                                            UkIcon("activity", cls="w-4 h-4 text-purple-500"),
                                            Span("Status: ", cls="text-sm text-muted-foreground"),
                                            Span(data_text=LandingState.deploy_status_signal, 
                                                cls="font-mono text-xs text-purple-500"),
                                            cls="gap-2"
                                        )
                                    ),
                                    cols=3, gap=4
                                ),
                                cls="px-6 py-4 border-t bg-gradient-to-r from-background/80 to-muted/80 backdrop-blur-sm"
                            ),
                            cls="relative group hover:shadow-2xl transition-all duration-500"
                        ),
                        cls="bg-card/80 backdrop-blur-sm border shadow-2xl overflow-hidden hover:border-primary/50 transition-all duration-500"
                    ),
                
                    # Live Result Preview with premium styling
                    Card(
                        # Premium browser header with live URL
                        Div(
                            DivLAligned(
                                Div(
                                    Span(cls="w-3 h-3 bg-red-500 rounded-full shadow-lg"),
                                    Span(cls="w-3 h-3 bg-yellow-500 rounded-full shadow-lg"),
                                    Span(cls="w-3 h-3 bg-green-500 rounded-full shadow-lg"),
                                    cls="flex gap-2"
                                ),
                                Div(
                                    UkIcon("globe", cls="w-4 h-4 mr-2 text-green-500"),
                                    Span("starmodel.dev/demo", cls="text-sm font-mono text-foreground bg-muted/50 px-3 py-1 rounded-full"),
                                    cls="flex items-center flex-1 justify-center"
                                ),
                                Button(
                                    UkIcon("rocket", cls="w-4 h-4 mr-1"),
                                    Span("Deploy", cls="text-xs font-semibold"),
                                    data_on_click=LandingState.simulate_deploy(),
                                    cls="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white px-3 py-1 rounded-lg text-xs transition-all duration-300 shadow-lg hover:shadow-xl flex items-center"
                                ),
                                cls="justify-between w-full"
                            ),
                            cls="px-6 py-4 border-b bg-gradient-to-r from-background/50 to-muted/50 backdrop-blur-sm"
                        ),
                    
                        # Live demo content with modern design
                        Div(
                            DivCentered(
                                # Demo app title with gradient
                                H1(
                                    UkIcon("star", cls="w-8 h-8 mr-3 text-yellow-500"),
                                    Span("StarModel Demo", cls="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"),
                                    cls="text-3xl font-bold mb-8 flex items-center justify-center"
                                ),
                                
                                # Interactive demo matching the code
                                Card(
                                    DivCentered(
                                        Div(
                                            Span("Message: ", cls="text-muted-foreground text-sm"),
                                            H2(data_text=LandingState.demo_message_signal, 
                                               cls="text-2xl font-bold text-primary mb-4"),
                                            cls="mb-6"
                                        ),
                                        
                                        Div(
                                            Span("Count: ", cls="text-muted-foreground mr-2"),
                                            Span(data_text=LandingState.live_counter_signal, 
                                                cls="font-mono text-3xl font-bold text-green-500"),
                                            cls="mb-6 flex items-center justify-center"
                                        ),
                                        
                                        DivLAligned(
                                            Button(
                                                UkIcon("plus", cls="w-4 h-4 mr-1"),
                                                "Click Me!",
                                                data_on_click=LandingState.pulse_counter(),
                                                cls="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-6 py-3 rounded-lg font-semibold transition-all duration-300 shadow-lg hover:shadow-xl flex items-center"
                                            ),
                                            Button(
                                                "Reset",
                                                data_on_click=LandingState.pulse_counter(0),
                                                cls="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded-lg transition-all duration-300"
                                            ),
                                            cls="gap-3 justify-center"
                                        ),
                                        cls="py-8"
                                    ),
                                    cls="bg-gradient-to-br from-background/50 to-muted/30 border-2 border-dashed border-primary/30 backdrop-blur-sm"
                                ),
                                
                                # Real-time performance metrics
                                Grid(
                                    Card(
                                        DivCentered(
                                            UkIcon("zap", cls="w-6 h-6 text-green-500 mb-2"),
                                            Span(data_text=LandingState.performance_score_signal, 
                                                cls="text-xl font-bold text-green-500"),
                                            P("Performance", cls="text-xs text-muted-foreground")
                                        ),
                                        cls="bg-green-50 border-green-200 hover:bg-green-100 transition-colors duration-300"
                                    ),
                                    Card(
                                        DivCentered(
                                            UkIcon("clock", cls="w-6 h-6 text-blue-500 mb-2"),
                                            Span(data_text=LandingState.response_time_signal, 
                                                cls="text-xl font-bold text-blue-500"),
                                            P("Response Time", cls="text-xs text-muted-foreground")
                                        ),
                                        cls="bg-blue-50 border-blue-200 hover:bg-blue-100 transition-colors duration-300"
                                    ),
                                    Card(
                                        DivCentered(
                                            UkIcon("activity", cls="w-6 h-6 text-purple-500 mb-2"),
                                            Span(data_text=LandingState.active_connections_signal, 
                                                cls="text-xl font-bold text-purple-500"),
                                            P("Active Users", cls="text-xs text-muted-foreground")
                                        ),
                                        cls="bg-purple-50 border-purple-200 hover:bg-purple-100 transition-colors duration-300"
                                    ),
                                    cols=3, gap=3, cls="mt-8"
                                )
                            ),
                            cls="p-8 bg-background/80 backdrop-blur-sm min-h-[500px]"
                        ),
                        cls="bg-card/80 backdrop-blur-sm border shadow-2xl hover:border-primary/50 transition-all duration-500"
                    ),
                    cols_lg=2, gap=8, cls="mb-16"
                ),
            
                # Premium CTA section
                DivCentered(
                    # Live metrics bar
                    Div(
                        Grid(
                            Div(
                                DivLAligned(
                                    UkIcon("github", cls="w-5 h-5 text-gray-600"),
                                    Span(data_text=LandingState.github_stars_signal, cls="font-bold text-foreground"),
                                    Span("stars", cls="text-muted-foreground text-sm"),
                                    cls="gap-2"
                                )
                            ),
                            Div(
                                DivLAligned(
                                    UkIcon("download", cls="w-5 h-5 text-green-600"),
                                    Span(data_text=LandingState.npm_downloads_signal, cls="font-bold text-foreground"),
                                    Span("downloads", cls="text-muted-foreground text-sm"),
                                    cls="gap-2"
                                )
                            ),
                            Div(
                                DivLAligned(
                                    UkIcon("code", cls="w-5 h-5 text-blue-600"),
                                    Span(data_text=LandingState.lines_written_signal, cls="font-bold text-foreground"),
                                    Span("lines written", cls="text-muted-foreground text-sm"),
                                    cls="gap-2"
                                )
                            ),
                            cols=3, gap=8, cls="justify-center items-center"
                        ),
                        cls="bg-card/50 backdrop-blur-sm border rounded-xl p-6 mb-12 shadow-lg"
                    ),
                    
                    # Main CTA buttons
                    DivLAligned(
                        Button(
                            UkIcon("rocket", cls="w-5 h-5 mr-2"),
                            "Start Building Now",
                            cls="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all duration-300 shadow-xl hover:shadow-2xl hover:-translate-y-1 flex items-center"
                        ),
                        A(
                            UkIcon("book-open", cls="w-5 h-5 mr-2"),
                            "View Documentation",
                            href="/docs",
                            cls="bg-card hover:bg-muted border-2 border-border hover:border-primary text-foreground px-8 py-4 rounded-xl text-lg font-semibold transition-all duration-300 shadow-lg hover:shadow-xl hover:-translate-y-1 flex items-center no-underline"
                        ),
                        cls="gap-6 justify-center"
                    )
                ),
                cls="mb-20"
            ),
            cls="py-20 relative z-10 max-w-7xl mx-auto px-4"
        ),
        cls="relative min-h-screen flex items-center overflow-hidden"
    )

def premium_features():
    """Premium feature showcase with interactive animations and modern design."""
    return Section(
        Container(
            DivCentered(
                H2(
                    "Powerful Features.", 
                    Br(),
                    Span("Zero Complexity.", cls="text-primary"),
                    cls="text-5xl md:text-6xl font-bold text-center mb-6"
                ),
                P("Everything you need to build modern reactive applications in Python", 
                  cls="text-xl text-muted-foreground mb-16 max-w-3xl text-center")
            ),
            
            # Feature cards with hover animations and interactive elements
            Grid(
                # Real-time Reactivity
                Card(
                    Div(
                        # Animated icon with gradient background
                        Div(
                            Div(
                                UkIcon("zap", cls="w-8 h-8 text-white"),
                                cls="bg-gradient-to-br from-yellow-400 to-orange-500 p-4 rounded-2xl shadow-lg group-hover:scale-110 transition-transform duration-300"
                            ),
                            cls="mb-6"
                        ),
                        
                        H3("Real-time Reactivity", cls="text-2xl font-bold text-foreground mb-4"),
                        P("Watch your UI update instantly as state changes. Zero manual DOM manipulation or complex state synchronization.",
                          cls="text-muted-foreground mb-6 leading-relaxed"),
                        
                        # Interactive demo widget
                        Card(
                            DivCentered(
                                P("Live Demo: ", cls="text-sm text-muted-foreground mb-2"),
                                Div(
                                    Span("Updates: ", cls="text-sm mr-2"),
                                    Span(data_text=LandingState.live_counter_signal, 
                                        cls="font-mono font-bold text-2xl text-yellow-500"),
                                    cls="flex items-center justify-center mb-3"
                                ),
                                Button(
                                    "✨ Update",
                                    data_on_click=LandingState.pulse_counter(),
                                    cls="bg-gradient-to-r from-yellow-400 to-orange-500 hover:from-yellow-500 hover:to-orange-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 shadow-md hover:shadow-lg"
                                )
                            ),
                            cls="bg-gradient-to-br from-yellow-50 to-orange-50 border-yellow-200 hover:border-yellow-300 transition-colors duration-300"
                        ),
                        cls="h-full flex flex-col"
                    ),
                    cls="group hover:shadow-2xl hover:-translate-y-2 transition-all duration-500 h-full"
                ),
                
                # Pure Python Development
                Card(
                    Div(
                        Div(
                            Div(
                                UkIcon("code", cls="w-8 h-8 text-white"),
                                cls="bg-gradient-to-br from-blue-500 to-purple-600 p-4 rounded-2xl shadow-lg group-hover:scale-110 transition-transform duration-300"
                            ),
                            cls="mb-6"
                        ),
                        
                        H3("Pure Python Stack", cls="text-2xl font-bold text-foreground mb-4"),
                        P("From backend logic to frontend components, everything in Python. No context switching, no JavaScript fatigue.",
                          cls="text-muted-foreground mb-6 leading-relaxed"),
                        
                        # Code demonstration
                        Div(
                            Pre(
                                Code(
                                    """@event
def handle_click(self):
    self.counter += 1
    # UI updates automatically!""",
                                    cls="language-python text-sm"
                                ),
                                cls="bg-gradient-to-br from-slate-900 to-slate-800 text-slate-100 p-4 rounded-lg text-sm font-mono leading-relaxed border border-slate-700"
                            ),
                            P("✨ Type-safe, autocomplete-friendly, and instantly reactive",
                              cls="text-xs text-blue-600 mt-3 text-center font-medium")
                        ),
                        cls="h-full flex flex-col"
                    ),
                    cls="group hover:shadow-2xl hover:-translate-y-2 transition-all duration-500 h-full"
                ),
                
                # Zero Configuration
                Card(
                    Div(
                        Div(
                            Div(
                                UkIcon("settings", cls="w-8 h-8 text-white"),
                                cls="bg-gradient-to-br from-green-500 to-emerald-600 p-4 rounded-2xl shadow-lg group-hover:scale-110 transition-transform duration-300"
                            ),
                            cls="mb-6"
                        ),
                        
                        H3("Zero Configuration", cls="text-2xl font-bold text-foreground mb-4"),
                        P("No webpack, no babel, no package.json madness. Install once and start building immediately.",
                          cls="text-muted-foreground mb-6 leading-relaxed"),
                        
                        # Installation demo
                        Div(
                            Div(
                                Div(
                                    Span("$", cls="text-green-500 mr-2 font-bold"),
                                    Span("pip install starmodel", cls="font-mono text-sm"),
                                    cls="bg-slate-900 text-white p-3 rounded-lg mb-3 flex items-center border border-slate-700"
                                ),
                                Div(
                                    UkIcon("check", cls="w-4 h-4 text-green-500 mr-2"),
                                    Span("Ready to build!", cls="text-sm font-medium text-green-600"),
                                    cls="flex items-center justify-center"
                                )
                            ),
                            cls="mt-auto"
                        ),
                        cls="h-full flex flex-col"
                    ),
                    cls="group hover:shadow-2xl hover:-translate-y-2 transition-all duration-500 h-full"
                ),
                cols_lg=3, gap=8, cls="mb-16"
            ),
            
            # Additional feature highlights
            Grid(
                # Performance & Scale
                Card(
                    DivLAligned(
                        Div(
                            UkIcon("trending-up", cls="w-12 h-12 text-blue-500 mb-4"),
                            H4("Enterprise Performance", cls="text-xl font-bold text-foreground mb-2"),
                            P("Built for scale with efficient server-sent events and optimized state synchronization.",
                              cls="text-muted-foreground text-sm")
                        ),
                        Div(
                            Grid(
                                Div(
                                    Span(data_text=LandingState.performance_score_signal, 
                                        cls="text-2xl font-bold text-blue-500"),
                                    P("Performance Score", cls="text-xs text-muted-foreground")
                                ),
                                Div(
                                    Span(data_text=LandingState.response_time_signal, 
                                        cls="text-2xl font-bold text-green-500"),
                                    P("Response Time", cls="text-xs text-muted-foreground")
                                ),
                                cols=2, gap=4
                            ),
                            cls="bg-muted/30 p-4 rounded-lg"
                        ),
                        cls="gap-6"
                    ),
                    cls="hover:shadow-xl transition-all duration-300"
                ),
                
                # Developer Experience
                Card(
                    DivLAligned(
                        Div(
                            UkIcon("heart", cls="w-12 h-12 text-red-500 mb-4"),
                            H4("Developer Experience", cls="text-xl font-bold text-foreground mb-2"),
                            P("Type-safe, IDE-friendly, with hot reload and debugging tools that actually work.",
                              cls="text-muted-foreground text-sm")
                        ),
                        Div(
                            DivLAligned(
                                UkIcon("check", cls="w-5 h-5 text-green-500"),
                                Span("Auto-completion", cls="text-sm"),
                                cls="gap-2"
                            ),
                            DivLAligned(
                                UkIcon("check", cls="w-5 h-5 text-green-500"),
                                Span("Type safety", cls="text-sm"),
                                cls="gap-2"
                            ),
                            DivLAligned(
                                UkIcon("check", cls="w-5 h-5 text-green-500"),
                                Span("Hot reload", cls="text-sm"),
                                cls="gap-2"
                            ),
                            cls="space-y-2 bg-muted/30 p-4 rounded-lg"
                        ),
                        cls="gap-6"
                    ),
                    cls="hover:shadow-xl transition-all duration-300"
                ),
                cols_lg=2, gap=8
            )
        ),
        cls="py-24 bg-gradient-to-b from-background to-muted/30"
    )

def social_proof_section():
    """Testimonials and social proof with GitHub stats and user feedback."""
    return Section(
        Container(
            DivCentered(
                H2("Loved by Python Developers Worldwide", 
                   cls="text-4xl md:text-5xl font-bold text-center mb-6"),
                P("Join thousands of developers building the future with StarModel", 
                  cls="text-xl text-muted-foreground mb-16 text-center")
            ),
            
            # GitHub stats bar
            Card(
                Grid(
                    Div(
                        DivCentered(
                            UkIcon("github", cls="w-8 h-8 text-gray-700 mb-2"),
                            Span(data_text=LandingState.github_stars_signal, 
                                cls="text-3xl font-bold text-foreground"),
                            P("GitHub Stars", cls="text-sm text-muted-foreground")
                        )
                    ),
                    Div(
                        DivCentered(
                            UkIcon("download", cls="w-8 h-8 text-green-600 mb-2"),
                            Span(data_text=LandingState.npm_downloads_signal, 
                                cls="text-3xl font-bold text-foreground"),
                            P("Weekly Downloads", cls="text-sm text-muted-foreground")
                        )
                    ),
                    Div(
                        DivCentered(
                            UkIcon("users", cls="w-8 h-8 text-blue-600 mb-2"),
                            Span(data_text=LandingState.active_connections_signal, 
                                cls="text-3xl font-bold text-foreground"),
                            P("Active Developers", cls="text-sm text-muted-foreground")
                        )
                    ),
                    Div(
                        DivCentered(
                            UkIcon("code", cls="w-8 h-8 text-purple-600 mb-2"),
                            Span(data_text=LandingState.lines_written_signal, 
                                cls="text-3xl font-bold text-foreground"),
                            P("Lines of Code", cls="text-sm text-muted-foreground")
                        )
                    ),
                    cols=4, gap=6
                ),
                cls="bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-primary/20 mb-16 p-8"
            ),
            
            # Testimonials grid
            Grid(
                # Testimonial 1
                Card(
                    Div(
                        # Quote
                        Div(
                            UkIcon("quote", cls="w-8 h-8 text-primary mb-4"),
                            P("\"StarModel completely changed how I think about web development. Building reactive UIs in pure Python feels like magic.\"",
                              cls="text-lg text-foreground mb-6 leading-relaxed italic"),
                            cls="mb-6"
                        ),
                        
                        # Author
                        DivLAligned(
                            Div(
                                Div("AS", cls="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-full flex items-center justify-center font-bold"),
                                cls="mr-4"
                            ),
                            Div(
                                P("Alex Smith", cls="font-semibold text-foreground"),
                                P("Senior Python Developer at TechCorp", cls="text-sm text-muted-foreground")
                            ),
                            cls="items-center"
                        )
                    ),
                    cls="hover:shadow-xl transition-all duration-300 h-full"
                ),
                
                # Testimonial 2
                Card(
                    Div(
                        Div(
                            UkIcon("quote", cls="w-8 h-8 text-primary mb-4"),
                            P("\"We migrated our entire dashboard from React to StarModel. Development speed increased 3x and our team loves it.\"",
                              cls="text-lg text-foreground mb-6 leading-relaxed italic"),
                            cls="mb-6"
                        ),
                        
                        DivLAligned(
                            Div(
                                Div("MJ", cls="w-12 h-12 bg-gradient-to-br from-green-500 to-blue-500 text-white rounded-full flex items-center justify-center font-bold"),
                                cls="mr-4"
                            ),
                            Div(
                                P("Maria Johnson", cls="font-semibold text-foreground"),
                                P("CTO at DataFlow Inc", cls="text-sm text-muted-foreground")
                            ),
                            cls="items-center"
                        )
                    ),
                    cls="hover:shadow-xl transition-all duration-300 h-full"
                ),
                
                # Testimonial 3
                Card(
                    Div(
                        Div(
                            UkIcon("quote", cls="w-8 h-8 text-primary mb-4"),
                            P("\"The learning curve was zero. If you know Python, you can build production-ready web apps with StarModel instantly.\"",
                              cls="text-lg text-foreground mb-6 leading-relaxed italic"),
                            cls="mb-6"
                        ),
                        
                        DivLAligned(
                            Div(
                                Div("DL", cls="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 text-white rounded-full flex items-center justify-center font-bold"),
                                cls="mr-4"
                            ),
                            Div(
                                P("David Lee", cls="font-semibold text-foreground"),
                                P("Full-Stack Developer & Indie Hacker", cls="text-sm text-muted-foreground")
                            ),
                            cls="items-center"
                        )
                    ),
                    cls="hover:shadow-xl transition-all duration-300 h-full"
                ),
                cols_lg=3, gap=8
            )
        ),
        cls="py-24 bg-muted/10"
    )

def premium_cta_section():
    """Premium call-to-action with getting started flow."""
    return Section(
        # Gradient background with overlay
        Div(
            cls="absolute inset-0",
            style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        ),
        
        Container(
            DivCentered(
                H2("Ready to Build the Future?", 
                   cls="text-5xl md:text-6xl font-bold text-white mb-6 text-center"),
                P("Join thousands of developers building reactive applications with StarModel", 
                  cls="text-xl text-white/90 mb-12 max-w-3xl text-center"),
                
                # Getting started flow
                Grid(
                    # Quick Start
                    Card(
                        Div(
                            UkIcon("rocket", cls="w-12 h-12 text-blue-600 mb-6"),
                            H3("Quick Start", cls="text-2xl font-bold text-foreground mb-4"),
                            P("Get your first StarModel app running in under 60 seconds", 
                              cls="text-muted-foreground mb-8"),
                            
                            # Terminal commands
                            Div(
                                Div(
                                    Span("$", cls="text-green-500 mr-3 font-bold"),
                                    Span("pip install starmodel", cls="font-mono text-white"),
                                    cls="bg-slate-900 p-4 rounded-lg mb-3 flex items-center border border-slate-700"
                                ),
                                Div(
                                    Span("$", cls="text-green-500 mr-3 font-bold"),
                                    Span("starmodel create my-app", cls="font-mono text-white"),
                                    cls="bg-slate-900 p-4 rounded-lg mb-6 flex items-center border border-slate-700"
                                ),
                                
                                Button(
                                    UkIcon("copy", cls="w-4 h-4 mr-2"),
                                    "Copy Commands",
                                    cls="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-all duration-300 shadow-lg hover:shadow-xl w-full flex items-center justify-center"
                                )
                            )
                        ),
                        cls="h-full"
                    ),
                    
                    # Learn & Explore
                    Card(
                        Div(
                            UkIcon("book-open", cls="w-12 h-12 text-purple-600 mb-6"),
                            H3("Learn & Explore", cls="text-2xl font-bold text-foreground mb-4"),
                            P("Dive deep with comprehensive docs, tutorials, and examples", 
                              cls="text-muted-foreground mb-8"),
                            
                            # Navigation buttons
                            Div(
                                A(
                                    UkIcon("book", cls="w-5 h-5 mr-2"),
                                    "Documentation",
                                    href="/docs",
                                    cls="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-semibold transition-all duration-300 shadow-lg hover:shadow-xl flex items-center justify-center mb-3 no-underline"
                                ),
                                A(
                                    UkIcon("play", cls="w-5 h-5 mr-2"),
                                    "Interactive Demo",
                                    href="/demo",
                                    cls="bg-gray-100 hover:bg-gray-200 text-gray-800 px-6 py-3 rounded-lg font-semibold transition-all duration-300 shadow-md hover:shadow-lg flex items-center justify-center mb-3 no-underline"
                                ),
                                A(
                                    UkIcon("bar-chart", cls="w-5 h-5 mr-2"),
                                    "Data Playground",
                                    href="/data-playground",
                                    cls="bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white px-6 py-3 rounded-lg font-semibold transition-all duration-300 shadow-lg hover:shadow-xl flex items-center justify-center mb-3 no-underline"
                                ),
                                A(
                                    UkIcon("github", cls="w-5 h-5 mr-2"),
                                    "View on GitHub",
                                    href="https://github.com/starmodel/starmodel",
                                    cls="bg-gray-800 hover:bg-gray-900 text-white px-6 py-3 rounded-lg font-semibold transition-all duration-300 shadow-lg hover:shadow-xl flex items-center justify-center no-underline"
                                )
                            )
                        ),
                        cls="h-full"
                    ),
                    cols_lg=2, gap=8, cls="max-w-5xl"
                )
            )
        ),
        cls="py-24 relative overflow-hidden"
    )

def premium_footer():
    """Comprehensive footer with links and branding."""
    return Footer(
        Container(
            # Main footer content
            Grid(
                # Brand section
                Div(
                    A(
                        UkIcon("star", cls="w-8 h-8 mr-3 text-primary"),
                        Span("StarModel", cls="text-2xl font-bold text-foreground"),
                        href="/",
                        cls="flex items-center mb-4 no-underline"
                    ),
                    P("Reactive state management for Python. Build interactive web applications without the complexity.",
                      cls="text-muted-foreground mb-6 max-w-sm leading-relaxed"),
                    
                    # Social links
                    DivLAligned(
                        A(UkIcon("github", cls="w-5 h-5"), 
                          href="https://github.com/starmodel/starmodel", 
                          cls="text-muted-foreground hover:text-primary transition-colors duration-300 p-2 rounded-lg hover:bg-muted"),
                        A(UkIcon("twitter", cls="w-5 h-5"), 
                          href="https://twitter.com/starmodel", 
                          cls="text-muted-foreground hover:text-primary transition-colors duration-300 p-2 rounded-lg hover:bg-muted"),
                        A(UkIcon("message-circle", cls="w-5 h-5"), 
                          href="https://discord.gg/starmodel", 
                          cls="text-muted-foreground hover:text-primary transition-colors duration-300 p-2 rounded-lg hover:bg-muted"),
                        cls="gap-2"
                    )
                ),
                
                # Product links
                Div(
                    H4("Product", cls="text-lg font-semibold text-foreground mb-4"),
                    Div(
                        A("Features", href="/#features", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Documentation", href="/docs", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Examples", href="/examples", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Playground", href="/playground", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Changelog", href="/changelog", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline")
                    )
                ),
                
                # Resources
                Div(
                    H4("Resources", cls="text-lg font-semibold text-foreground mb-4"),
                    Div(
                        A("Getting Started", href="/docs/getting-started", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Tutorials", href="/tutorials", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Blog", href="/blog", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Community", href="/community", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Support", href="/support", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline")
                    )
                ),
                
                # Company
                Div(
                    H4("Company", cls="text-lg font-semibold text-foreground mb-4"),
                    Div(
                        A("About", href="/about", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Team", href="/team", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Careers", href="/careers", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Privacy", href="/privacy", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline"),
                        A("Terms", href="/terms", cls="block text-muted-foreground hover:text-primary transition-colors duration-300 mb-2 no-underline")
                    )
                ),
                cols_lg=4, gap=8, cls="mb-12"
            ),
            
            # Bottom bar
            Div(
                DivLAligned(
                    P("© 2024 StarModel. All rights reserved.", 
                      cls="text-muted-foreground text-sm"),
                    DivLAligned(
                        Span("Made with", cls="text-muted-foreground text-sm mr-1"),
                        UkIcon("heart", cls="w-4 h-4 text-red-500 mr-1"),
                        Span("by the StarModel team", cls="text-muted-foreground text-sm"),
                        cls="items-center"
                    ),
                    cls="justify-between w-full items-center"
                ),
                cls="border-t pt-8"
            )
        ),
        cls="bg-muted/20 py-16"
    )

@rt('/')
@page_template(title="⭐ StarModel - Reactive State Management for Python")
def index(req: Request):
    """Revolutionary landing page showcasing StarModel's reactive magic."""
    state = LandingState.get(req)
    
    return Main(
        state,
        premium_hero(),
        premium_features(), 
        social_proof_section(),
        premium_cta_section(),
        premium_footer(),
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