from fasthtml.common import *
from monsterui.all import *
from faststate import *
import asyncio

rt = APIRouter()

class CounterState(State):
    """Enhanced counter with persistence and real-time sync."""
    count: int = 0
    last_updated_by: str = ""
    update_count: int = 0
    
    # Auto-registration configuration
    _config = StateConfig(
        scope=StateScope.GLOBAL,
        auto_persist=True,
        persistence_backend="memory",
        ttl=30
    )
    
    @event(method="post")
    async def increment(self, amount: int = 1, user: str = "Anonymous"):      
        self.update_count += 1
        for i in range(amount):
            self.count += 1
            self.last_updated_by = user
            await asyncio.sleep(i/1000)
            yield Div(f"Counter incremented by {i+1} by {user}",id="message", cls="font-mono text-sm text-green-600")
    
    @event(method="post")
    async def decrement(self, amount: int = 1, user: str = "Anonymous"):
        self.update_count += 1
        for i in range(amount):
            self.count -= 1
            self.last_updated_by = user
            await asyncio.sleep(i/1000)
            yield Div(f"Counter decremented by {i+1} by {user}",id="message", cls="font-mono text-sm text-red-600")
        
    
    @event(method="post")
    async def reset(self, user: str = "Anonymous"):
        self.update_count += 1
        for i in range(abs(self.count)):
            if self.count > 0: self.count -= 1 
            else: self.count += 1
            self.last_updated_by = user
            await asyncio.sleep(i/1000)
            yield Div(f"Counter reset by {user}",id="message", cls="font-mono text-sm text-blue-600")


@rt('/counter')
def global_counter(req: Request, sess: dict, auth: str = None):
    """
    Global counter demo with persistence and real-time synchronization.
    """
    counter = CounterState.get(req, sess, auth)
    username = auth or sess.get('auth', 'Anonymous')
    
    return Main(
        counter,
        counter.LiveDiv(heartbeat=0),
        Div(
            H1("🔢 Global Counter Demo", cls="text-3xl font-bold mb-6"),
            P("This counter is shared globally across all users and persisted to database. Open multiple tabs to see the counter update in real-time.", 
                cls=TextPresets.muted_sm+"mb-6"),
            
            # Counter display
            Div(
                Div(
                    Div(
                        Span(data_text="$count", cls="text-7xl font-bold text-primary"),
                        cls="text-center mb-4"
                    ),
                    Div("Total updates: ", Span(data_text="$update_count"), cls="font-mono text-secondary"),
                    Div(f"Current user: {username}", cls="font-mono text-secondary"),
                    Div("Last updated by: ", Span(data_text="$last_updated_by"), cls="font-mono text-secondary mb-2"),
                    Div(id="message", cls="font-mono text-secondary mb-2"),
                    cls="p-6 border border-primary rounded mb-6 text-center"
                ),
                cls="mb-6"
            ),
            
            # Counter controls
            Div(
                Div(
                    Button("-100", 
                            data_on_click=CounterState.decrement(100, username),
                            cls="bg-red-700 text-white px-4 py-2 rounded mr-2"),
                    Button("-10", 
                            data_on_click=CounterState.decrement(10, username),
                            cls="bg-red-600 text-white px-4 py-2 rounded mr-2"),
                    Button("-1", 
                            data_on_click=CounterState.decrement(1, username),
                            cls="bg-red-400 text-white px-4 py-2 rounded mr-2"),
                    Button("Reset", 
                            data_on_click=CounterState.reset(username),
                            cls="bg-gray-500 text-white px-4 py-2 rounded mr-2"),
                    Button("+1", 
                            data_on_click=CounterState.increment(1, username),
                            cls="bg-green-400 text-white px-4 py-2 rounded mr-2"),
                    Button("+10", 
                            data_on_click=CounterState.increment(10, username),
                            cls="bg-green-600 text-white px-4 py-2 rounded mr-2"),
                    Button("+100", 
                            data_on_click=CounterState.increment(100, username),
                            cls="bg-green-700 text-white px-4 py-2 rounded"),
                    cls="text-center mb-6"
                ),
                cls="mb-6"
            ),
            
            # # Custom increment
            # Div(
            #     Form(
            #         Input(name="amount", placeholder="Amount", type="number", value="1", data_bind="$amount",
            #                 cls="border rounded px-3 py-2 mr-2 w-24"),
            #         Button("+", type="submit", 
            #                 cls="bg-blue-500 text-white px-4 py-2 rounded mr-2"),
            #         data_on_submit=CounterState.increment(user=username),
            #         cls="mb-6"
            #     ),
            #     cls="text-center mb-6"
            # ),
            
            A("← Back to Home", href="/", cls="text-secondary hover:underline"),
            
            cls="container mx-auto p-8 max-w-3xl"
        )
    )

