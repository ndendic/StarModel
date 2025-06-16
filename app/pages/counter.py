from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from pages.templates import app_template
from entities import CounterEntity

rt = APIRouter()


@rt('/counter')
@app_template("Counter")
def global_counter(req: Request):
    """
    Global counter demo with persistence and real-time synchronization.
    """
    counter = CounterEntity.get(req)
    username = req.session.get("user") or "Anonymous"
    
    return Main(
        counter,
        # counter.PollDiv(),
        Div(
            H1("🔢 Global Counter Demo", cls="text-3xl font-bold mb-6"),
            P("This counter is shared globally across all users and persisted to database. Open multiple tabs to see the counter update in real-time.", 
                cls=TextPresets.muted_sm+"mb-6"),
            
            # Counter display
            Div(
                Div(
                    Div(
                        Span(data_text=CounterEntity.count_signal, cls="text-7xl font-bold text-primary"),
                        cls="text-center mb-4"
                    ),
                    Div("Total updates: ", Span(data_text=CounterEntity.update_count_signal), cls="font-mono text-secondary"),
                    Div(f"Current user: {username}", cls="font-mono text-secondary"),
                    Div("Last updated by: ", Span(data_text=CounterEntity.last_updated_by_signal), cls="font-mono text-secondary mb-2"),
                    Div(id="message", cls="font-mono text-secondary mb-2"),
                    cls="p-6 border border-primary rounded mb-6 text-center"
                ),
                cls="mb-6"
            ),
            
            # Counter controls
            Div(
                Div(
                    Button("-100", 
                            data_on_click=CounterEntity.decrement(100, username),
                            cls="bg-red-700 text-white px-4 py-2 rounded mr-2"),
                    Button("-10", 
                            data_on_click=CounterEntity.decrement(10, username),
                            cls="bg-red-600 text-white px-4 py-2 rounded mr-2"),
                    Button("-1", 
                            data_on_click=CounterEntity.decrement(1, username),
                            cls="bg-red-400 text-white px-4 py-2 rounded mr-2"),
                    Button("Reset", 
                            data_on_click=CounterEntity.reset(username),
                            cls="bg-gray-500 text-white px-4 py-2 rounded mr-2"),
                    Button("+1", 
                            data_on_click=CounterEntity.increment(1, username),
                            cls="bg-green-400 text-white px-4 py-2 rounded mr-2"),
                    Button("+10", 
                            data_on_click=CounterEntity.increment(10, username),
                            cls="bg-green-600 text-white px-4 py-2 rounded mr-2"),
                    Button("+100", 
                            data_on_click=CounterEntity.increment(100, username),
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
                    data_on_submit=CounterEntity.increment(user=username),
                    cls="mb-6"
                ),
                cls="text-center mb-6"
            ),
            
            A("← Back to Home", href="/", cls="text-secondary hover:underline"),
            
            cls="container mx-auto p-8 max-w-3xl"
        ),
        id="content",
    )

