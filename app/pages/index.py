from fasthtml.common import *
from monsterui.all import *
from faststate import *
from pages.templates import app_template

rt = APIRouter()

class MyState(State):
    """Session-scoped state - each user session gets its own instance."""
    myInt: int = 0
    myStr: str = "Hello"
    tick_count: int = 0

    @event
    def increment(self, amount: int):
        self.myInt += amount

    @event("/decrement")
    def decrement(self, amount: int):
        self.myInt -= amount

    @event("/reset")
    def reset(self):
        self.myInt = 0

    @event()
    def set_myStr(self, myStr: str = myStr):
        self.myStr = myStr
        
    @event(selector="#ticker-box", merge_mode="inner")
    def start_ticking(self):
        self.tick_count += 1
        # return H4("Tick #", Span(data_text=self.signal("tick_count")), cls="text-red-500")
        return self.card()
    
    def card(self):
        return Div(
            self,
            H2(f"{self.namespace} Card", cls=TextT.primary),
            H4("myStr: ", Span(data_text=MyState.myStr_signal, cls=TextT.primary)),
            H4("myInt: ", Span(data_text=MyState.myInt_signal, cls=TextT.primary)),
            H4("tick_count: ", Span(data_text=MyState.tick_count_signal, cls=TextT.primary)),
            cls="bg-secondary-foreground p-4 rounded mb-4"
        )


@rt('/')
@app_template("Home")
def index(req: Request):
    """
    Main page demonstrating session-scoped state with simple .get() method.
    Clean and explicit state resolution!
    """
    auth = req.session.get("user")
    
    # Simple, explicit state resolution
    my_state = MyState.get(req)
    return Main(
        # Welcome message
        Div(
            H1("🚀 BackState Demo", cls="text-4xl font-bold text-center mb-6"),
            P("Showcasing automatic dependency injection with different state scopes", 
                cls="text-center mb-8"),
            cls="mb-8"
        ),
        
        # State information
        Div({"data-persist__session":True}),
        my_state.card(),  # Uses __ft__ method for rendering
        Div(
            H2("📊 Current State Info", cls="text-2xl font-bold mb-4"),
            Div(
                Div(f"Session ID: {req.cookies.get('session_', 'auto-generated')[:100]}", cls="font-mono text-sm"),
                Div(f"Auth: {auth or 'Not authenticated'}", cls="font-mono text-sm"),
                Div(f"State ID: {my_state.id}", cls="font-mono text-sm"),
                cls="bg-gray-100 p-4 rounded mb-6"
            ),
            cls="mb-8"
        ),
                
        # Interactive controls
        Div(
            H3("🎮 Interactive Controls", cls="text-xl font-bold mb-4"),
            Input(data_bind=my_state.signal("myStr"), data_on_change=MyState.set_myStr(), 
                    cls="border rounded px-3 py-2 mb-4 w-full", placeholder="Edit text..."),
                    
            H4("Counter Controls", cls="font-bold mb-2"),
            Div(
                Button("- Decrease", data_on_click=MyState.decrement(1), 
                        cls="bg-red-500 text-white px-4 py-2 rounded mr-2"),
                Button("🔄 Reset", data_on_click=MyState.reset(), 
                        cls="bg-gray-500 text-white px-4 py-2 rounded mr-2"),
                Button("+ Increase", data_on_click=MyState.increment(1), 
                        cls="bg-green-500 text-white px-4 py-2 rounded"),
                cls="mb-4"
            ),
            
            H4("Ticker Demo", cls="font-bold mb-2"),
            Div(id="ticker-box", cls="bg-yellow-50 p-4 rounded mb-4 min-h-[60px]"),
            Button("Start Tick", data_on_click=MyState.start_ticking(), 
                    cls="bg-blue-500 text-white px-4 py-2 rounded"),
            cls="mb-8"
        ),
        
        # Navigation
        Div(
            H3("🔗 Navigation", cls="text-xl font-bold mb-4"),
            Div(
                A("👤 User Profile", href="/profile", cls="bg-blue-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                A("⚙️ Admin Panel", href="/admin", cls="bg-purple-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                A("📦 Product Demo", href="/product/123", cls="bg-green-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                A("💬 Real-time Chat", href="/chat", cls="bg-orange-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                A("🔢 Global Counter", href="/counter", cls="bg-indigo-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                A("📊 System Status", href="/status", cls="bg-cyan-500 text-white px-4 py-2 rounded mr-2 mb-2 inline-block"),
                A("🔒 Login Demo", href="/login", cls="bg-gray-500 text-white px-4 py-2 rounded mb-2 inline-block"),
            ),
            cls="mb-8"
        ),
        
        cls="container mx-auto p-8 max-w-4xl"
    )

@rt('/playground')
def playground(req: Request):
    my_state = MyState.get(req)
    return Main(
        my_state,
        Div(data_persist=True),
        Div({"data-on-online__window": MyState.sync(req)}),
        Div({"data-on-load": MyState.sync(req)}),
        Div(
           H1("Playground"),
           Div(data_text="$myInt",data_persist=True, cls="text-4xl font-bold text-center mb-6"),
           Input(data_bind="$myInt"), 
           cls="container mx-auto p-8 max-w-4xl"
        )
    )