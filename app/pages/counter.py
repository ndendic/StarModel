from starmodel import *
from fasthtml.common import *
from monsterui.all import *
from pages.templates import app_template

import asyncio

class Counter(Entity): 
    """Enhanced counter with persistence and real-time sync."""
    model_config = {
        "arbitrary_types_allowed": True,
        "persistence_backend": MemoryRepo(),
        "auto_persist": True,
        "ttl": 10,
    }
    
    count: int = 0
    last_updated_by: str = ""
    update_count: int = 0
    id: str = "global_counter"
    
    @event
    async def increment(self, amount: int = 1, user: str = "Anonymous"):      
        self.update_count += 1
        for i in range(amount):
            self.count += 1
            self.last_updated_by = user
            yield Div(f"Counter incremented by {i+1} by {user}",id="message", cls="font-mono text-sm text-green-600")
            await asyncio.sleep(1/(i+1))
    
    @event(method="POST")
    async def decrement(self, amount: int = 1, user: str = "Anonymous"):
        self.update_count += 1
        for i in range(amount):
            self.count -= 1
            self.last_updated_by = user
            yield Div(f"Counter decremented by {i+1} by {user}",id="message", cls="font-mono text-sm text-red-600")
            await asyncio.sleep(1/(i+1))
        
    
    @event(method="POST")
    async def reset(self, user: str = "Anonymous"):
        self.update_count += 1
        for i in range(abs(self.count)):
            if self.count > 0: self.count -= 1 
            else: self.count += 1
            self.last_updated_by = user
            yield Div(f"Counter reset by {user}",id="message", cls="font-mono text-sm text-blue-600")
            await asyncio.sleep(1/(i+1))

rt = APIRouter()


@rt('/counter')
@app_template("Counter")
def global_counter(req: Request):
    """
    Global counter demo with persistence and real-time synchronization.
    """
    counter = Counter.get(req)
    username = req.session.get("user") or "Anonymous"
    
    return Main(
        counter,
        # counter.Poll(),
        Div(
            H1("🔢 Global Counter Demo", cls="text-3xl font-bold mb-6"),
            P("This counter is shared globally across all users and persisted to database. Open multiple tabs to see the counter update in real-time.", 
                cls=TextPresets.muted_sm+"mb-6"),
            
            # Counter display
            Div(
                Div(
                    Div(
                        Span(data_text=Counter.Scount, cls="text-7xl font-bold text-primary"),
                        cls="text-center mb-4"
                    ),
                    Div("Total updates: ", Span(data_text=Counter.Supdate_count), cls="font-mono text-secondary"),
                    Div(f"Current user: {username}", cls="font-mono text-secondary"),
                    Div("Last updated by: ", Span(data_text=Counter.Slast_updated_by), cls="font-mono text-secondary mb-2"),
                    Div(id="message", cls="font-mono text-secondary mb-2"),
                    cls="p-6 border border-primary rounded mb-6 text-center"
                ),
                cls="mb-6"
            ),
            
            # Counter controls
            Div(
                Div(
                    Button("-100", 
                            data_on_click=Counter.decrement(100, username),
                            cls="bg-red-700 text-white px-4 py-2 rounded mr-2"),
                    Button("-10", 
                            data_on_click=Counter.decrement(10, username),
                            cls="bg-red-600 text-white px-4 py-2 rounded mr-2"),
                    Button("-1", 
                            data_on_click=Counter.decrement(1, username),
                            cls="bg-red-400 text-white px-4 py-2 rounded mr-2"),
                    Button("Reset", 
                            data_on_click=Counter.reset(username),
                            cls="bg-gray-500 text-white px-4 py-2 rounded mr-2"),
                    Button("+1", 
                            data_on_click=Counter.increment(1, username),
                            cls="bg-green-400 text-white px-4 py-2 rounded mr-2"),
                    Button("+10", 
                            data_on_click=Counter.increment(10, username),
                            cls="bg-green-600 text-white px-4 py-2 rounded mr-2"),
                    Button("+100", 
                            data_on_click=Counter.increment(100, username),
                            cls="bg-green-700 text-white px-4 py-2 rounded"),
                    cls="text-center mb-6"
                ),
                cls="mb-6"
            ),
            
            # Custom increment
            Div(
                Form(
                    Input(name="amount", placeholder="Amount", type="number", value="1", data_bind="$amount",
                            cls="border rounded px-3 py-2 mr-2 w-24"),
                    Button("+", type="submit", 
                            cls="bg-blue-500 text-white px-4 py-2 rounded mr-2"),
                    data_on_submit=Counter.increment(user=username),
                    cls="mb-6"
                ),
                cls="text-center mb-6"
            ),
            
            A("← Back to Home", href="/", cls="text-secondary hover:underline"),
            
            cls="container mx-auto p-8 max-w-3xl"
        ),
        id="content",
    )

