# StarModel

**Entity-Centric Reactive Development for FastHTML**

StarModel enables you to define your application's data structure and behavior in one place, minimizing configuration overhead and maximizing development speed. Build reactive web applications entirely in Python by encapsulating both backend logic and frontend interactivity around your entities.

## Core Philosophy

**Stop separating your data from your behavior.** StarModel brings entity-driven development to web applications:

- **State Models** - Define your data structure and business logic in unified Python classes
- **Event Decorators** - Turn methods into interactive SSE endpoints in a same way you use route `@rt` decorators
- **Datastar Integration** - Automatic frontend reactivity without writing JavaScript

## Technology Stack

- [**FastHTML**](https://fastht.ml/) - Server-side HTML generation and routing
- [**Datastar**](https://data-star.dev/) - Lightweight (~15KB) frontend reactivity via SSE  
- [**Pydantic**](https://pydantic.dev/) - Type-safe data models with validation

## Quick Start

```bash
git clone https://github.com/ndendic/StarModel.git
cd StarModel
uv sync
python app/main.py  # Visit http://localhost:5001
```

or install package like

```bash
pip install git+https://github.com/ndendic/StarModel.git
```

## Entity-Centric Development

Below is full example you can run (uses MonsterUI for styling)
```python
from fasthtml.common import *
from monsterui.all import *
from starmodel import *

app, rt = fast_app(
    htmx=False,
    hdrs=(
        Theme.zinc.headers(),
        datastar_script, # <-- Load datastar cdn script
    ),
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
    def reset(self):
        self.count = 0
        self.update_count += 1

@rt
def index(req: Request):
    counter = Counter.get(req) # <-- Get your model/state from request or overide `get` for custom logic
    return Main(
        counter, # <-- auto add signals, sync and persistance
        H1("🔢 Counter Demo"),
        # Counter display
        Card(
            Div(
                Span(data_text=Counter.count_signal, cls=TextT.primary + "text-7xl font-bold"),
                cls="text-center mb-2"
            ),
            Div("Total updates: ", Span(data_text=Counter.update_count_signal), cls=TextT.primary),
            cls=CardT.default + "text-center my-6",
        ),            
        # Counter controls
        Div(
            Div(
                Button("-10", data_on_click=Counter.decrement(10), cls=ButtonT.secondary),
                Button("-1", data_on_click=Counter.decrement(1), cls=ButtonT.secondary),
                Button("Reset", data_on_click=Counter.reset(), cls=ButtonT.secondary),
                Button("+1", data_on_click=Counter.increment(1), cls=ButtonT.secondary),
                Button("+10", data_on_click=Counter.increment(10), cls=ButtonT.secondary),
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

states_rt.to_app(app) # <-- Import and add state routes

if __name__ == "__main__":
    serve(reload=True, port=8080)
```

## Why This Matters

### 🎯 **Entity-Driven Architecture**
Your `User`, `Product`, `Order` entities contain both data schema and business logic. No more scattering behavior across controllers, services, and frontend code.

### ⚡ **Zero Configuration Reactivity**  
The `@event` decorator automatically creates HTTP endpoints and generates Datastar-compatible URLs. Your methods csn become interactive without routing setup. You can still add all parameters you tipically add to your `@route` decorators and expect extraction of standard Starlette `request`, `session`, and other entities + new `datastar` object that can be extracted from the request automatically with other signlas sent.

#### Here is one example - note that it's smaller bit taken examples and cannot be used "as-is"
```python
class Sale(BaseModel):
    name: str
    email: str
    amount: int

class DashboardState(State):
    
    sales: int = 0
    subscriptions: int = 0
    active_now: int = 0
    total_revenue: int = 0
    recent_sales: List[Sale] = []
    
    @event
    async def add_sales(self, amount: int = 0, name: str = "Unknown", email: str = "Unknown"):
        self.sales += 1
        self.total_revenue += amount
        sale = Sale(name=name, email=email, amount=amount)
        self.recent_sales.append(sale)
        yield self.recent_sales_card()
        yield self.sales_chart()

    def recent_sales_card(self):
        return Card(cls="col-span-3", id="recent-sales-card")(
            Div(cls="space-y-8 px-4")(
                *[
                    AvatarItem(n, e, d)
                    for (n, e, d) in (
                        *[(sale.name, sale.email, f"+${sale.amount}") for sale in self.recent_sales],
                    )
                ]
            ),
            header=Div(
                H3("Recent Sales"), P("You made 265 sales this month.", cls=TextPresets.muted_sm)
            ),
        )
    
    def sales_chart(self):
        return Div(id="sales-chart")(
                Apex_Chart(
                    chart_type=ChartT.area,
                    series=[
                        {"name": "2024", "data": [sale.amount for sale in self.recent_sales]},
                    ],
                    categories=[sale.name for sale in self.recent_sales],
                    fill={"type": "gradient", "gradient": {"shadeIntensity": 1, "opacityFrom": 0.4, "opacityTo": 0.1}},
                    cls='max-w-md max-h-md',
                )
            ),

@rt("/dashboard")
def dashboard(request):
    state = DashboardState.get(request)
    return Div(cls="space-y-4")(
        ...
        Form(
            Input(type="text", name="name", data_bind="$name", placeholder="Name"),
            Input(type="email", name="email", data_bind="$email", placeholder="Email"),
            Input(type="number", name="amount", data_bind="$amount", placeholder="Amount"),
            Button("Add Sales", type="submit"),
            data_on_submit=DashboardState.add_sales(),
            
        )
        ...
    )
```

### 🔄 **Seamless State Synchronization**
Changes to your Python objects instantly update the frontend via Server-Sent Events. Two-way data binding works automatically. `State` class comes with some automatic Datastar helpers that can be used in the front-end:
 - `MyModel.myArg_signal` class atribute will return `$myArg` or `$MyModel.myArg` Datastar formated string based on the configured usage of namaspace
 - `MyModel.myEvent(maybe, some, args)` will be converted to `@get('/path/to/MyModel/endpoint')` also `@post`, `@put` and other will be used if specified in `@event` `methods` args.
 - `myModelInstance` has opinionated `__ft__` function that deturns an empty `Div` with all the Model signals, persistance options, and sync calls. Overide this method to set how your instance is shown in your `FT` elements.
 - There is much more, so please feel free to explore source code to get max out of it.

### 📦 **Minimal Peripheral Setup**
No Redux stores, no API layer design, no frontend state management. Just define your entities and interact with them.

## Storage Options
StarModel comes with 3 model storage options, 2 enabled by Datastar persistance in client session and cliend local storage, and one for backend server memory, but it's built to allow user to hook up any custom persistence options like Redis or Database. Just overide standard methods for `get`, `save`, `delete` or extend with your custom logic. 

```python
from starmodel import StateStore

class UserProfile(State):
    name: str = ""
    preferences: dict = {}
    
    # Choose your persistence layer
    model_config = {
        "store": StateStore.SERVER_MEMORY,    # Server memory (default)  
        # "store": StateStore.CLIENT_SESSION, # Browser sessionStorage
        # "store": StateStore.CLIENT_LOCAL,   # Browser localStorage
        # "store": StateStore.CUSTOM,         # Custom logic
        "persistence_backend": memory_persistence, # <-- Instance of your persistance manager class
    }
```

## Other Helpful Resources
You can try to combine this library with other FastHTML/Datastar/Pydantic helper libraries for even better dev experience. Here are some of them: 
[ft-datastar](https://github.com/banditburai/ft-datastar) 
[datastar_py attribute helpers](https://github.com/starfederation/datastar/tree/develop/sdk/python)
[fh-pydantic-form](https://github.com/Marcura/fh-pydantic-form)
[FastSQLModel](https://github.com/ndendic/FastSQLModel)


## Demo Application

Run `python app/main.py` to see examples of:
- Session-based counters
- Real-time chat 
- Form handling with client storage
- Multi-user collaboration

## Contributing

This project focuses on eliminating the complexity of modern web development by returning to entity-centric design patterns. Contributions welcome!

## License

MIT License