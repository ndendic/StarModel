from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from pages.templates import app_template
from datastar_py import attribute_generator as data

rt = APIRouter()

class MyState(State):
    """Session-scoped state - each user session gets its own instance."""
    myInt: int = 0
    myStr: str = "Hello from StarModel"
    myList: list = []

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
    def add_to_list(self, item: str):
        self.myList.append(item)
        return self.card()
    
    def card(self):
        return Div(
            self,
            H2(f"{self.namespace} Card", cls=TextT.primary),
            H4("myStr: ", Span(data_text=MyState.myStr_signal, cls=TextT.primary)),
            H4("myInt: ", Span(data_text=MyState.myInt_signal, cls=TextT.primary)),
            H4("myList: ", Span(data_text=MyState.myList_signal if len(MyState.myList_signal) > 0 else "Empty", cls=TextT.primary)),
            cls="bg-secondary-foreground p-4 rounded mb-4"
        )


@rt('/')
@app_template("Home")
def index(req: Request):
    """
    Main page demonstrating session-scoped state with simple .get() method.
    Clean and explicit state resolution!
    """
    # Simple, explicit state resolution
    my_state = MyState.get(req)
    return Main(
        # Welcome message
        Div(
            H1("🚀 StarModel Demo", cls="text-4xl font-bold text-center mb-6"),
            P("Showcasing automatic dependency injection with different state scopes", 
                cls="text-center mb-8"),
            cls="mb-8"
        ),
        
        # State information
        H2("📊 Current State Info", cls="text-2xl font-bold mb-4"),
        Div({"data-persist__session":True}),
        my_state.card(),  # Uses __ft__ method for rendering       
                
        # Interactive controls
        Div(
            H3("🎮 Interactive Controls", cls="text-xl font-bold mb-4"),
            FormLabel("Set myStr"),
            Input(data_bind=my_state.signal("myStr"), data_on_change=MyState.set_myStr(), 
                    cls="border rounded px-3 py-2 mb-4 w-full", placeholder="Edit text..."),
                    
            H4("myInt Controls", cls="font-bold mb-2"),
            Div(
                Button("- Decrease", data_on_click=MyState.decrement(1), 
                        cls="bg-red-500 text-white px-4 py-2 rounded mr-2"),
                Button("🔄 Reset", data_on_click=MyState.reset(), 
                        cls="bg-gray-500 text-white px-4 py-2 rounded mr-2"),
                Button("+ Increase", data_on_click=MyState.increment(1), 
                        cls="bg-green-500 text-white px-4 py-2 rounded"),
                cls="mb-4"
            ),
            FormLabel("Add to myList"),
            Input(data_bind="$item", data_on_change=MyState.add_to_list(), 
                    cls="border rounded px-3 py-2 mb-4 w-full", placeholder="Add some item.."),
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