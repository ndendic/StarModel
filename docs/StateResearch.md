# Class-Based State Management with FastHTML & Datastar

## Overview

FastHTML and Datastar together enable building reactive web apps in pure Python with minimal JavaScript. **FastHTML** is a Python web framework that maps Python code 1:1 to HTML/HTTP, providing _FastTags_ (FT) components for HTML elements and route decorators for defining endpoints. **Datastar** is a lightweight hypermedia front-end library (only ~15KB) that combines the reactive state of Alpine.js with the server interactivity of htmx. Datastar uses **signals** (reactive variables) and HTML `data-*` attributes for two-way data binding on the frontend. Crucially, Datastar relies on **Server-Sent Events (SSE)** for transport – every backend response is an SSE stream, allowing the server to push unlimited updates to the client in real time.

This guide outlines a **class-based state management system** that leverages FastHTML for routing/UI and Datastar for reactivity and SSE updates. The goals of this system are:

- **Declarative Routes & Events:** Use Python decorators on a state class to automatically register HTTP routes and event handlers.
    
- **Two-Way Binding:** Achieve two-way data binding between Python state and the frontend via Datastar signals and SSE (so that changes on either side propagate instantly).
    
- **Reactive Updates:** Push UI updates to the browser whenever state attributes change on the server, using SSE events.
    
- **FastHTML + Datastar Integration:** Use FastHTML’s component and routing system with Datastar’s `data-*` binding attributes and SSE transport (no custom JavaScript needed on the client).
    
- **Optional Persistence:** Allow the state class to double as a **Pydantic/SQLModel** data model for validation and database persistence, so state can be saved/loaded seamlessly.
    

By the end, we’ll have a design where you can define a stateful class like:

```python
class MyState(State):           # define reactive state model  
    myInt: int = 0             # attributes with type hints  
    myStr: str = "Hello"  

    @event
    def increment(self, amount: int):
        self.myInt += amount   # update state  
        return Div(self.myInt) # optionally return new fragment/UI
```

And use it in FastHTML routes like:

```python
@rt('/')
def index():
    # Render UI with data-* bindings and event triggers
    return Div(
        H1("Counter: ", Span(data_text="$myInt")),               # display bound state 
        Button("Increase by 1", data_on_click=MyState.increment(1))
        , data_signals=MyState.get_signals()                     # embed initial state
    )
```

In this example, clicking the button triggers the `increment` event on the backend, which updates the `myInt` state and immediately pushes the new value to the UI via SSE, updating the `<span>` text. We’ll now break down how to implement each piece of this system in detail.

## Automatic Route and Event Registration via Decorators

FastHTML provides a route decorator (often obtained via `app, rt = fast_app()`) to map URLs to Python functions. We will extend this idea by creating two decorators: `@rt` for page routes and `@event` for state event handlers:

- **`@rt` (Route Decorator):** Registers a function as an HTTP route. In FastHTML, `@rt("/path")` wraps a function to serve GET requests at that URL. Under the hood, FastHTML’s app is built on Starlette (ASGI), so each route becomes an ASGI endpoint. Our usage will be similar – for example `@rt('/')` on a function will serve the main page. The route handler can return FastHTML FT components (which get rendered to HTML) or SSE generators for Datastar (discussed later).
    
- **`@event` (Event Decorator):** Used inside state classes to mark methods as event handlers. An _event_ in this context is a backend action (often triggered by a frontend interaction) that will update state and possibly return some UI update. The `@event` decorator will automatically register the method as an endpoint (just like `@rt` would) and tie it to the state class.
    

**How it works:** When the class is defined, the `@event` decorator can intercept the method definition. For example, Python decorators run at definition time, so `@event` can assign a URL route for that method. A common pattern is to generate a unique path based on the class and method name. For instance, `MyState.increment` could be exposed at `/mystate/increment` (optionally with an ID or session token if needed). The decorator would use FastHTML’s routing under the hood to register this endpoint.

One way to implement this is using a metaclass or class decorator: upon class creation, find all methods marked with `@event` and call `app.add_route()` or FastHTML’s `rt` for each. Alternatively, the `@event` decorator itself can call `rt()` immediately. For example:

```python
def event(func):
    # Determine an endpoint path for this event
    route_path = f"/{func.__qualname__.replace('.', '/')}"
    # Register the route with SSE response handling
    rt(route_path)(func)  
    return func  # return original function unmodified
```

This simplistic snippet assumes `rt` is in scope and registers the method as a GET/POST route. In practice, you might include the HTTP method (e.g., use `@rt.post` for state-mutating events) or allow `@event` to accept an HTTP method. The main idea is that developers do not manually write routing boilerplate for each event – the system _auto-registers_ it.

**Calling the Event from the UI:** We want a nice syntax to trigger these events from the frontend. In the example, we wrote `Button(..., data_on_click=MyState.increment(1))`. How does this work? Likely, `MyState.increment` is not a normal instance method call here – instead, the class’s method decorator could make it a descriptor that returns something when accessed on the class. For instance, `MyState.increment(1)` could be defined to return the event’s URL (with `var1=1` as a query parameter). Another approach is to have `MyState.increment` store metadata about its route, and override `__call__` to produce a hyperlink. FastHTML’s FT allows arbitrary element attributes, so if `MyState.increment(1)` yields the string `"/mystate/increment?amount=1"`, then `data_on_click=...` becomes `data-on-click="/mystate/increment?amount=1"` in HTML. We might even produce the special Datastar action syntax like `@get('/mystate/increment?amount=1')`.

For example, the `event` decorator could attach a function attribute for the URL template:

```python
func._route = route_path  # attach the computed path
def call_with_args(*args):
    # format args into query string or path
    qs = "?" + urlencode(dict(param_values))
    return route_path + qs
func.__call__ = staticmethod(lambda *args: call_with_args(*args))
```

With this, calling `MyState.increment(1)` returns the URL string. In practice, you might implement it more cleanly (perhaps returning a small `EventCall` object that FastHTML can convert to a string). The outcome is the same: the template can easily embed the event call in an HTML attribute.

By automatically registering routes and providing a way to reference them in the UI, we keep event wiring declarative. The developer just writes a method with `@event` and uses it; the system handles mapping it to an endpoint and constructing the URL.

## Two-Way Data Binding with Datastar (SSE Signals)

Datastar’s frontend uses **signals** for state, enabling two-way binding between HTML elements and backend state. On the HTML side, you declare signals with attributes like `data-bind` and display or use them with `data-text`, `data-show`, etc. For example, `<input data-bind-input />` creates a signal named “input” bound to that field’s value. If either the input’s value _or the signal’s value_ changes, the other is automatically updated. This is achieved through Datastar’s internal model – essentially, it keeps a JavaScript object of signal values (a “store”) and updates the DOM when signals change, and vice versa for user input.

To leverage this, our Python State class can be thought of as the authoritative source of truth for certain signals. Each attribute of the state (e.g. `myInt`, `myStr`) will correspond to a Datastar signal (e.g. `$myInt`, `$myStr` in the DOM). The binding works as follows:

- **Initializing Signals:** When serving the initial page, we include the state’s current values in the HTML using a `data-signals` attribute. Datastar allows merging initial signal values into its global store via `data-signals`. For example, if `myInt = 0` and `myStr = "Hello"`, we can include an element like:
    
    ```html
    <div data-signals='{"myInt": 0, "myStr": "Hello"}'></div>
    ```
    
    This will pre-populate Datastar’s signals `$myInt` and `$myStr` on the client. In FastHTML, we can generate this easily: if `state` is a Pydantic model, `state.model_dump()` (or `.dict()` in Pydantic v1) gives a dict of all fields. We JSON-encode that and set it as `data_signals=state_dict`. FastHTML will render it as the `data-signals` attribute. By merging signals on page load, the UI elements bound to those signals start with the correct values.
    
- **Binding in the UI:** We use Datastar data-* attributes in our FastHTML components. For instance, to display a state value, we use `Span(data_text="$myInt")` – this tells Datastar to insert the value of signal `$myInt` into this span’s text. To allow user input to update state, we could use an input bound to the signal. For example, `Input(type="text", data_bind="myStr")` would tie the input field to signal `$myStr` (so typing in the box updates `$myStr`, and if `$myStr` changes from the server, the input box updates). In our simple counter example, the button’s `data-on-click` triggers a backend event rather than directly setting the signal, but Datastar also supports directly setting signals from the UI (`data-on-click="$myInt = $myInt + 1"` could increment locally). However, using the backend event lets us enforce server-side logic and optionally persist changes.
    
- **Backend SSE Updates:** The key to two-way binding is that when the **backend state changes**, it must notify the frontend. Datastar uses **Server-Sent Events** to propagate changes from server to browser. Specifically, the server can send a special SSE event of type `datastar-merge-signals` with a payload of updated signal values. When the browser receives this, it merges those values into the global signals store, and any bound UI elements update automatically. This is how our Python class will push updates.
    

In summary, Datastar provides the mechanism for two-way binding: **user actions -> update signals (via requests)**, and **server state -> update UI (via SSE signals)**. Our job is to connect our class’s attributes to these signals and produce the proper SSE events on changes.

## Pushing State Updates to the Frontend via SSE

Unlike traditional HTTP responses that return a full HTML page or fragment, Datastar expects **all responses as SSE streams** (even if it’s a single event). This allows a route to send multiple messages over time, or just one, using the SSE data format. Under SSE, the server keeps the response open and can send events like:

```
event: datastar-merge-signals  
data: signals {"myInt": 42}
```

Each event is text-formatted and ends with a double newline as per SSE spec. The Datastar client library listens to these events and updates the DOM accordingly.

**Datastar-Py SDK:** To simplify sending these events, we can use the `datastar-py` Python SDK. This provides a `ServerSentEventGenerator` (often imported as `SSE`) with helper methods for each event type. For example, `SSE.merge_signals({"myInt": 42})` will produce an SSE event that tells the client to update the `myInt` signal to 42. Likewise, `SSE.merge_fragments([html_str])` can send an HTML fragment to be merged into the DOM. Under the hood these format the `event:` and `data:` lines properly.

We integrate SSE in our event routes. When an event handler (decorated with `@event`) is called, it will typically:

1. **Update the State Object:** e.g. `self.myInt += amount`. This changes the Python object’s attribute. If the State inherits from Pydantic/BaseModel, the attribute is stored in the model.
    
2. **Prepare SSE Output:** We determine what needs to be sent to the client. In most cases, the changed state values should be pushed as signals. We can compare the state before and after, or simply always send the relevant fields. For efficiency, sending only changed signals is ideal (imagine a state with many fields). We can track changes by storing a copy of the state (or using Pydantic’s `__dict__` diff). For example:
    
    ```python
    old_vals = self.model_dump()  # get current state as dict (Pydantic v2)
    result = func(self, *args, **kwargs)  # call the original event method
    new_vals = self.model_dump()
    changed = {k: v for k,v in new_vals.items() if v != old_vals.get(k)}
    ```
    
    Suppose `changed` is `{"myInt": 6}` (myInt was incremented from 5 to 6). We then create an SSE generator to yield this update: `yield SSE.merge_signals(changed)`. If multiple values changed, they can all be included in one `merge_signals` call (it accepts a dict of signal names to values).
    
3. **Optional HTML Fragment:** If the event handler returns an FT component (e.g. `return Div(self.myInt)`), we can send that as well. Datastar supports merging HTML fragments via `datastar-merge-fragments` events. This can be useful if the event needs to add or replace a section of the DOM that isn’t covered by simple text/attribute binding. FastHTML’s FT components can be converted to HTML strings (FastHTML likely has an internal `to_html()` or just relying on Starlette’s response conversion). We could do: `fragment_html = to_html(result)` and then `yield SSE.merge_fragments([fragment_html])`. We should also specify how to merge – e.g., using an element ID and `mergeMode` if replacing a specific element. For example, if our Div had `id="counterVal"`, we could instruct Datastar to morph that ID. However, in many cases we might avoid needing fragments by using signals and `data-text`. In our counter, we don’t actually need to send a fragment; updating the signal is enough to update the displayed number.
    
4. **Return an SSE Response:** The route should return an SSE-compatible response. With frameworks like FastAPI or Starlette, we would return a `StreamingResponse` or similar. FastHTML likely has built-in support: recall that FastHTML is built on Starlette, so returning a generator or async generator that yields bytes will be sent as a streaming response. The Datastar-Py SDK provides framework-specific helpers (they mention support for FastHTML explicitly). For instance, if using FastAPI, one might return `StreamingResponse(SSE_generator(), media_type='text/event-stream')`. In our integration, we can rely on FastHTML’s `serve()` or use the SDK’s helper to wrap our generator. The key is to set the correct SSE headers (Content-Type: `text/event-stream`, Cache-Control: `no-cache`, Connection: `keep-alive`). The SDK defines `SSE_HEADERS` for this purpose.
    

**Example:** Using our `increment` event, the decorated function could be implemented like:

```python
@event
def increment(self, amount: int):
    before = self.model_dump()
    self.myInt += amount
    after = self.model_dump()
    changed = {k:v for k,v in after.items() if v != before.get(k)}
    # SSE generator function
    async def stream():
        # if any state changed, send signals update
        if changed:
            yield SSE.merge_signals(changed)
        # no fragment in this case since UI is bound to signals
    return stream()
```

Because the `@event` decorator handles route registration, the above would be invoked when the client performs `GET /mystate/increment?amount=1`. The server responds with an SSE stream that (in this case) immediately yields one `datastar-merge-signals` event and then completes. The Datastar client receives the new `myInt` value and updates any bound elements.

**Why SSE?** SSE is a natural fit here because it’s one-directional (server→client) and built on standard HTTP. Datastar specifically chooses SSE over WebSockets because SSE works over HTTP/2 and HTTP/3, integrates with REST semantics, and can leverage HTTP features (e.g. easy to scale via event streams). SSE also allows sending multiple pieces of data incrementally. For example, an event handler could first send an immediate UI update and then continue to stream progress updates or additional data over time – all within the scope of one request. Our state system can take advantage of that if needed (for instance, long-running operations could stream updates).

## Integrating FastHTML for UI and Datastar for Transport

Bridging FastHTML and Datastar involves combining FastHTML’s server-side rendering with Datastar’s front-end reactivity. Here are the integration points and patterns:

- **Including Datastar Script:** The Datastar JS library must be loaded in the page. Typically, you include `<script type="module" src="https://cdn.jsdelivr.net/gh/starfederation/datastar@1.0.0-beta.11/bundles/datastar.js"></script>` in the HTML. In FastHTML, you can ensure this script tag is present in your layout. For example, if using a `Head()` component, add `Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@1.0.0-beta.11/bundles/datastar.js", type="module")`. FastHTML allows adding custom header includes (as shown in an SSE example using HTMX extension). With Datastar, do this once on page load.
    
- **Using Datastar Data Attributes in FastHTML:** FastHTML’s FT components accept keyword arguments for attributes. Any underscore in the name is converted to a hyphen, so `data_on_click=...` becomes `data-on-click` in HTML (just like `hx_get` becomes `hx-get`). We leverage this to put Datastar directives in our elements:
    
    - `data_on_click="@get('/path')"` triggers a GET request via Datastar when clicked. (Datastar’s `@get()` syntax is analogous to htmx’s `hx-get` but goes through SSE).
        
    - `data_on_input="$$put('/path')"` can send a PUT request on input events (the `$$` indicates sending the current store state, as described in Datastar docs, though for simplicity we might stick to @get/@post with specific payloads).
        
    - Binding attributes like `data_bind="fieldName"` and display attributes like `data_text="$fieldName"` can be set on our FT components to connect to signals.
        
    
    In practice, our FastHTML route might create the UI using these attributes. For example:
    
    ```python
    @rt("/")
    def index():
        state = MyState()  # new state instance (or retrieved from session/DB)
        return Html(
            Head(Script(src=DATASTAR_CDN, type="module")),
            Body(
                Div(  # embed initial signals
                    data_signals=json.dumps(state.model_dump())
                ),
                H1("Counter: ", Span(data_text="$myInt", id="counterVal")),
                Button("Increase by 1", 
                       data_on_click=f"@get('/mystate/increment?amount=1')",
                       data_indicator="fetching")  # optional: show spinner
            )
        )
    ```
    
    A few things to note: We include `data_signals` with `state` values. The Span shows `$myInt`. The Button uses `@get('/mystate/increment?amount=1')` which Datastar will interpret as: on click, perform a GET to that URL and treat the response as SSE actions. We could also use a shorter helper by calling our Python method: `Button(..., data_on_click=MyState.increment(1))` as mentioned, which would internally format the same string. We add `data_indicator="fetching"` which is a Datastar attribute to automatically show a loading indicator on the button while the request is in progress (purely a UX enhancement).
    
- **Session or State Management on Server:** We need to ensure that when the increment event hits the server, it operates on the correct `MyState` instance. If our app is multi-user or multi-session, each user should have their own state. FastHTML provides session support via Starlette sessions (using a server-side dict keyed by a cookie). We can tie state to session ID. For example, when creating `state = MyState()`, we might store it in `session['MyState']`. However, note that session data must be JSON-serializable; storing a raw object isn’t directly possible. Instead, we could store the state’s ID or primary key. If using SQLModel, the state could be persisted to a database table – then we store `session['my_state_id']`. On each request/event, we load the object (from DB or an in-memory registry) by that ID. Alternatively, maintain a global in-memory dict of state instances keyed by session ID (or a UUID) if persistence isn’t needed. The decision depends on use-case:
    
    - **Ephemeral state per session:** Use in-memory storage or attach to the FastHTML session. Simpler but state is lost on restart and not shared.
        
    - **Persistent state:** Define `MyState` as a SQLModel with a table. On first use, create and save it (e.g. `session.add(state); session.commit()`). Pass the state’s ID to the client (perhaps as part of the route URL or as a hidden signal). Every event request should include an identifier (session cookie or explicit param) so the backend knows which state to update.
        
    
    For our example, we might use the session cookie implicitly (Datastar sends cookies with requests by default, so the server can get session). In code, the event handler could accept a `session` param (FastHTML will inject it), then do: `state = session.get('MyState')` to retrieve it. If not found, handle accordingly (perhaps the session expired or we create a new one).
    
- **Consistency with Datastar’s expectations:** As noted, every response should be SSE. That means even the initial page load route (`index`) might need to output SSE events rather than raw HTML, if we strictly follow Datastar’s pattern. However, in practice, you can serve an initial HTML page that includes the Datastar script and initial signals (as we showed). Datastar’s docs often show using `data-on-load="$$get('/stream')"` to immediately open an SSE connection on page load. We could adopt that pattern: Instead of embedding signals directly, we could open a stream that sends them. For simplicity, we did a direct include, which is fine for initial state. The hybrid approach is acceptable: load HTML, then let Datastar handle subsequent interactions via SSE. If we wanted truly SPA-like behavior, we might even serve an almost empty page and then use SSE to populate it; but that’s optional.
    

In short, FastHTML handles template rendering and route wiring, while Datastar handles dynamic interaction. By carefully constructing HTML with `data-*` attributes and responding with SSE events, the two combine to provide a reactive experience without writing custom JavaScript. The FastHTML app remains purely Python code that can manipulate the DOM remotely.

## Optional State Persistence with SQLModel and Pydantic

It’s often useful if the state object can be saved to a database or validated easily. We achieve this by making our `State` class inherit from **Pydantic** (for data modeling) and optionally SQLModel (for DB persistence). Pydantic allows defining class fields with type annotations which become structured, validated fields. SQLModel is built on Pydantic and SQLAlchemy, making a class behave as _both_ a Pydantic model and a SQLAlchemy ORM model. In other words, **a single class can serve as a Pydantic schema and a database table model at the same time**.

By using SQLModel, our `State` inherits `BaseModel` functionality (from Pydantic) and `DeclarativeBase` from SQLAlchemy. We can then:

- Define fields in the class with types (and default values if desired). For example, `myInt: int = 0` and `myStr: str = ""`. These become Pydantic fields (for JSON validation/serialization) and, if we designate the class as a table, columns in the database. We might add `id: Optional[int] = Field(default=None, primary_key=True)` if using a database primary key.
    
- **Validation:** Pydantic will validate types on assignment or initialization. For instance, if someone tried to set `MyState.myInt = "not an int"`, it would raise an error or at least not validate. This helps maintain correct data. You can also add Pydantic validators or constraints (e.g. ensure a string isn’t empty, or an int is within a range).
    
- **Persistence:** To actually persist, we must configure a database (SQLModel can use SQLite, Postgres, etc.). Suppose we have `class MyState(SQLModel, table=True): ...` with a table name or let it auto-generate one. We can then use SQLModel’s session (which is just a SQLAlchemy session) to add and commit instances. After calling `session.commit()`, our state has an `id`. Next time, we can query `state = session.get(MyState, id)` to retrieve it. This is particularly useful if we want the state to persist across server restarts or share state between processes.
    
- **Using Non-Persistent Mode:** If we don’t specify `table=True` or a `tablename`, the class is effectively just a Pydantic model. We can still use it for all our state logic and validation, but it won’t create a DB table. This might be fine for ephemeral session state. The design allows opting in to persistence without changing the rest of the code – “the same class can also serve as a data model” in both senses: an in-memory data model and a DB model.
    

For example, to define a persistent state:

```python
from sqlmodel import SQLModel, Field

class State(SQLModel):
    __abstract__ = True  # base class not a table itself
    # (could include common mixins or utility methods here)

class MyState(State, table=True):             # table=True to create DB table
    id: Optional[int] = Field(default=None, primary_key=True)
    myInt: int = 0
    myStr: str = "Hello"
```

If we prefer not to persist, we could omit `table=True` and the `id` field:

```python
class MyState(State):  # not a table, acts as Pydantic model only
    myInt: int = 0
    myStr: str = "Hello"
```

Either way, `myInt` and `myStr` are standard Pydantic fields, so methods like `model_dump()` (Pydantic v2) or `.dict()` (v1) work to serialize state to JSON (for `data-signals` or SSE). If persistent, we get the benefit of storing to DB – for example, one could decorate the event methods to call `session.commit()` after updating, so changes are saved. This could be integrated by injecting a DB session into the event (FastHTML could potentially provide a session via dependency injection similar to how FastAPI might, or simply use a global session object for simplicity in a small app).

Another advantage of using Pydantic/SQLModel is easy integration with FastAPI/FastHTML request handling. If an event expects data from the client (e.g., a form submit sending JSON or form fields), Pydantic models or fields can be used to parse those automatically. FastHTML supports typed parameters in route functions (including Pydantic models) for parsing inputs. So if an event needed a complex payload, we could define it as taking a Pydantic model or just primitives and let the framework parse query parameters accordingly.

## Implementation Example and Architecture Walk-through

Putting it all together, here’s a simplified implementation sketch for clarity:

```python
from fasthtml.common import *       # FastHTML imports (for fast_app, components, etc)
from datastar_py import ServerSentEventGenerator as SSE, SSE_HEADERS
from sqlmodel import SQLModel, Field
import json

app, rt = fast_app()  # initialize FastHTML app and route decorator

# Base state class with optional persistence
class State(SQLModel):
    __abstract__ = True  # base class not mapped to a table
    # (Could include methods for SSE broadcasting, etc.)

# Decorator for state event methods
def event(func):
    # Determine route path from class and function name
    # e.g. MyState.increment -> /MyState/increment
    cls_name = func.__qualname__.split('.')[0]   # e.g. "MyState"
    route = f"/{cls_name}/{func.__name__}"
    # Wrap original function to produce SSE response
    async def sse_handler(request, *args, **kwargs):
        # Locate state instance (e.g. via session or id)
        session = request.session  # (FastHTML provides session if param named 'request' or similar)
        state = session.get(cls_name)
        # Parse any query params for function arguments:
        # FastHTML/Starlette can extract these via function signature if named same.
        # Here, assume *args, **kwargs already contain the parsed parameters like 'amount'.
        # Capture state before
        old_vals = state.model_dump()
        # Call original event logic
        result = func(state, *args, **kwargs)
        # Compute changes and prepare SSE events
        new_vals = state.model_dump()
        changed = {k: v for k, v in new_vals.items() if old_vals.get(k) != v}
        # Use datastar-py to generate SSE data
        def stream():
            if changed:
                # send updated signals (as JSON string)
                yield SSE.merge_signals(changed)
            if result is not None:
                # if function returned an FT component, send as fragment
                html = to_html(result)              # FastHTML utility to render component to HTML string
                yield SSE.merge_fragments([html])   # send fragment (could specify selector if needed)
        # Return streaming response (with correct headers)
        return Response(stream(), media_type="text/event-stream", headers=SSE_HEADERS)
    # Register the SSE handler as a route (probably as GET)
    rt(route)(sse_handler)
    # Return a callable for convenience (to generate URLs)
    def trigger(*args, **kwargs):
        # Construct query string from args
        params = []
        for arg, param in zip(args, func.__annotations__.keys()):
            if param == 'return': 
                continue  # skip return annotation
            params.append(f"{param}={arg}")
        qs = ("?" + "&".join(params)) if params else ""
        return f"{route}{qs}"
    return staticmethod(trigger)  # return as staticmethod attached to class

# Example state class
class MyState(State, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    myInt: int = 0
    myStr: str = "Hello"

    @event
    def increment(self, amount: int):
        self.myInt += amount
        # No explicit return needed (we could return a Div, but we'll rely on signals)
```

And the route that uses it:

```python
@rt("/")  # main page
def index(request):
    # Get or create state for this session
    session = request.session
    state = session.get('MyState')
    if not state:
        state = MyState()        # new instance
        session['MyState'] = state
        # If persistent, also add to DB and commit to get an id.
    # Build HTML response
    return Html(
        Head(Script(src="https://cdn.jsdelivr.net/gh/starfederation/datastar@1.0.0-beta.11/bundles/datastar.js", type="module")),
        Body(
            # Embed initial state values as signals
            Div(data_signals=json.dumps(state.model_dump())),
            H1("Counter: ", Span(data_text="$myInt")),
            Button("Increase by 1", data_on_click=MyState.increment(1))
        )
    )
```

_(Note: The above code is illustrative; actual implementation details may vary. FastHTML might require slightly different handling for sessions or a different way to get request context in handlers. Also, `to_html()` would be a function converting an FT component to a string – FastHTML’s internals likely do this when returning components.)_

**Workflow Explanation:** When a client requests “/”, the `index` route runs. It either retrieves an existing `MyState` from the session or creates one, then returns an HTML page. This page includes the Datastar script and a `data-signals` div to initialize `$myInt` and `$myStr` in the browser. The UI shows the current counter and a button. The button’s `data-on-click` is set to call our `increment` event (via SSE). When clicked, the Datastar library performs an HTTP GET to `/MyState/increment?amount=1` (the URL our `@event` set up).

On the server, FastHTML routes that URL to the `sse_handler` we registered. In `sse_handler`, we retrieve the `MyState` instance for this session, then call the original `increment` logic. After incrementing, `state.myInt` is updated (say from 0 to 1). We compute that `{"myInt": 1}` changed, and use `SSE.merge_signals` to yield an event updating that signal. We return this as a streaming response with `text/event-stream` content type. The client receives the SSE message, and Datastar merges the new signal value into its store. As a result, the `<span data-text="$myInt">` in the DOM automatically updates to “1” (the Datastar runtime handles this reactivity). All of this occurs almost instantly, creating a smooth two-way bound incrementing counter.

If we had more complex UI changes (e.g., adding elements), we could send fragments. For instance, an event could return a new `<li>` item to append to a list; our handler would yield `merge_fragments` with `mergeMode append`. But often, designing the UI with bound signals (text, attributes, `data-show`, etc.) is more efficient, letting the front-end handle the DOM update when data changes.

**State Persistence:** In the above example, `MyState` is a SQLModel table, but we didn’t actually use a database session for brevity. In a real app, you would initialize a database (e.g., `create_engine` and sessionmaker). On first creation of `state`, you’d do `db_session.add(state); db_session.commit()`. That assigns `state.id`. You might also store `state.id` in the cookie or session. Later, instead of storing the object in `session` (which is not serializable), you could just store the ID and fetch from DB each time. The trade-off is simplicity vs persistence: in-memory session storage is easiest but won’t scale beyond one process or survive restarts; database storage is more durable.

Because SQLModel classes are also Pydantic models, using them in FastHTML/Starlette is straightforward. They can be JSON-serialized (for signals), and you can even return them in API routes if needed. The combination of Pydantic’s **data validation** and SQLAlchemy’s **ORM** in SQLModel means our state class is a true model in the MVC sense – containing data and logic (the event methods) together.

## Technical Considerations and Architecture Reasoning

- **Decorators & Metaprogramming:** Using decorators for route and event registration keeps the syntax clean and close to the usage in frameworks like FastAPI or Flask. It also ties the URL design to the code structure (e.g., `Class.method` -> `/class/method` route), which can be intuitive in small apps. Python’s introspection allows us to automate what would otherwise be repetitive wiring of endpoints. We ensure that `@event` registers routes that output SSE, aligning with Datastar’s requirement for SSE in responses. The decorators abstract away the SSE boilerplate so the developer can simply write “what happens” when an event occurs (changing state, returning a component), and not worry about manually constructing responses.
    
- **SSE vs WebSockets:** SSE was chosen as the push mechanism because it integrates with HTTP and is simpler to set up than WebSockets for many use cases. Datastar explicitly favors SSE for compatibility with HTTP/2+ and simpler streaming. SSE provides enough functionality for most real-time updates (the server can push any number of messages). It’s one-way, but that’s acceptable here since user->server events use normal HTTP requests (Datastar covers that with `@get`, `@post` etc.). This aligns well with FastHTML, which is built on Starlette and can easily stream HTTP responses. We avoid the complexity of maintaining WebSocket connections and instead use standard HTTP requests paired with a long-lived SSE response when needed.
    
- **Datastar Integration:** By using Datastar’s `data-*` conventions, we offload a lot of frontend logic to a declarative approach. The HTML carries expressions and triggers that Datastar evaluates (e.g., `$myInt`, `$myStr`, `@get('/endpoint')`). This drastically reduces custom JS – the front-end logic is encoded in attributes and handled by Datastar’s small runtime. The approach is very much “Hypermedia as UI”. Our Python code doesn’t manipulate the DOM directly; it sends high-level instructions (like “update this signal” or “insert this fragment”) and the client library does the rest. This keeps the server code simple and focused on state and data.
    
- **SQLModel/Pydantic for State:** This choice provides strong **data integrity** and convenience. Declaring state as a class with type annotations means we get **documentation** and **validation** for free. It’s clear what fields exist and their types. Pydantic (and thus SQLModel) will ensure that any data coming in (if any, e.g. via APIs) conforms to these types, and it can also constrain values (with validators). The optional persistence is a huge win for not duplicating models – as the SQLModel docs highlight, you don’t have to make separate ORM and Pydantic classes; one model can serve both purposes. In an application where, say, `MyState` should be saved (maybe it represents a user’s form or a game state), we can directly write `state = MyState(**data); session.add(state)` etc., then later use `state` in our FastHTML views, all with the same class definition.
    
- **Scalability:** The described architecture works well for moderate interactive apps. SSE is robust for many clients, but if you anticipate thousands of concurrent users each with an open SSE, ensure your server (and ASGI server) is tuned for many open connections (SSE connections are lightweight, but they are held open). Also, using a database for state means you can scale the backend horizontally (since state isn’t only in-memory). The trade-off is performance (a DB round-trip for each event) vs convenience. In many cases, an in-memory state per process with sticky sessions can work; for more robustness, persistence is there.
    
- **Security:** Since we’re auto-generating routes for events, be mindful of exposure. It’s wise to namespace them (we did by prefixing with class name). If the state is user-specific, those routes should likely be protected (e.g., only accessible to that user’s session). One could include a unique token or use the session cookie for that. FastHTML/Starlette sessions help by scoping state to a user. Always validate inputs (Pydantic helps here for types, but logic validation is on you). Also, SSE endpoints should ideally not be publicly cacheable (we set proper headers for that).
    
- **Developer Experience:** Using this pattern, developers can think in terms of a **single source of truth** (the Python state class) and **event-driven updates**. It’s quite close to the model-view concept: the State class is the model, FastHTML FT components define the view (with Datastar enhancing it for reactivity), and the event methods act as controllers (updating the model and producing view changes). This synergy can make complex interactive apps easier to reason about, without manually writing JavaScript or managing a separate client-side state. All state transitions happen in Python, which is often simpler to debug and test. You could even write unit tests for the state class’s methods (since they’re just Python functions modifying attributes).
    

## Conclusion

By combining FastHTML and Datastar, we achieve a powerful full-stack reactive framework in Python. The class-based `State` system provides an organized way to manage UI state:

- **Decorators** register routes and events seamlessly, keeping routing logic out of the business code.
    
- **SSE-based binding** ensures UI and server state stay in sync in real time, using Datastar’s efficient signal mechanism for updates.
    
- **FastHTML components** let us build UIs in Python with attributes corresponding to Datastar’s reactivity model.
    
- **Pydantic/SQLModel** give our state strong typing and optional persistence, unifying the in-memory state and stored data model.
    

This architecture essentially brings the convenience of front-end frameworks (like React’s state or Svelte stores) into the Python backend world, using web standards (HTML over SSE) to communicate. It embraces a hypermedia philosophy: the server defines not just the content but how it can change (through hypermedia links or in this case, event endpoints embedded in attributes), and the client (Datastar) simply follows those instructions.

With the patterns described here, you can build rich interactive apps (forms with live validation, collaborative interfaces with live updates, dashboards, etc.) all in Python. The key is leveraging the strengths of each tool: FastHTML for rapid UI composition and routing, and Datastar for minimalistic realtime front-end reactivity. The result is a compact yet powerful stack for modern web applications.

**References:** The design draws on concepts from official Datastar documentation (signals, SSE events) and FastHTML’s architecture:

- Datastar signals and two-way binding are documented in the Datastar Guide.
    
- SSE event formats like `datastar-merge-signals` and fragment merging are in Datastar’s reference.
    
- The Datastar Python SDK usage (e.g., `SSE.merge_signals`) is illustrated in the project README.
    
- FastHTML’s approach to routes, components, and Starlette integration is summarized in its docs and community examples.
    
- SQLModel’s ability to serve as both Pydantic model and ORM model is highlighted in its documentation, aligning with our goal of a unified state/data class.