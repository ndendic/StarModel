import asyncio
import inspect
import json
import urllib.parse
import uuid

from datastar_py import SSE_HEADERS
from datastar_py import ServerSentEventGenerator as SSE
from fasthtml.common import *
from fasthtml.core import APIRouter
from monsterui.franken import *
from sqlmodel import Field, SQLModel

rt = APIRouter()

class ReactiveState(SQLModel):
    # id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # utility: send just-changed fields over SSE --------------------------- #
    def _diff_and_events(self, before: dict, after: dict):
        changed = {k: v for k, v in after.items() if before.get(k) != v}
        if changed:
            yield SSE.merge_signals(changed)
    
    def __ft__(self):
        return Div(
            H2(f"State : {self.__class__.__name__} ({self.id})", cls="mt-4"),
            *[Div(f"{k}: ",Span(data_text=f"${k}")) for k, v in self.model_dump().items()],
            data_signals=json.dumps(self.model_dump()))

_STATE_REGISTRY: dict[str, ReactiveState] = {}

def _get_state(session: dict, cls: type[ReactiveState]) -> ReactiveState:
    sid_key = f"{cls.__name__}_id"
    sid = session.get(sid_key)

    if sid and (state := _STATE_REGISTRY.get(sid)):
        return state

    state = cls()
    _STATE_REGISTRY[state.id] = state
    session[sid_key] = state.id

    return state


VERBS = {"get", "post", "put", "patch", "delete"}

# ------------------------------------------------------------------ #
def event(_func=None, *, method: str = "get", selector: str = None, merge_mode: str = "morph"):
    """
    Usage examples
        @event
        @event(method="post")
    """
    method = method.lower()
    if method not in VERBS:
        raise ValueError(f"Unsupported HTTP verb: {method!r}")

    # real decorator (keeps variable / function order identical to your version)
    def _decorator(func):

        route_path = "/" + func.__qualname__.replace(".", "/")

        async def _handler(request):
            state = _get_state(request.session,
                               globals()[func.__qualname__.split(".")[0]])
            before = state.model_dump()

            sig = inspect.signature(func)
            bound = {}
            for name, param in list(sig.parameters.items())[1:]:  # skip 'self'
                raw = request.query_params.get(name)
                if raw is None and param.default is inspect._empty:
                    return f"Missing query param: {name}"
                if raw is not None:
                    ann = typing.get_origin(param.annotation) or param.annotation
                    bound[name] = ann(raw) if ann in (int, float, bool) else raw

            out = await func(state, **bound) if asyncio.iscoroutinefunction(func) else func(state, **bound)
            after = state.model_dump()

            async def stream():
                # Send initial state changes
                for ev in state._diff_and_events(before, after):
                    yield ev
                
                if out is not None:
                    # Check if output is an async generator (for streaming)
                    if hasattr(out, '__aiter__'):
                        async for fragment in out:
                            yield SSE.merge_fragments([to_xml(fragment)], selector=selector, merge_mode=merge_mode)
                    else:
                        fragments = []
                        # Handle different return types
                        if hasattr(out, '__iter__') and not isinstance(out, (str, FT)):
                            # Multiple fragments
                            fragments = [to_xml(f) for f in out]
                        else:
                            # Single fragment
                            fragments = [to_xml(out)]

                        # Use decorator parameters or defaults
                        yield SSE.merge_fragments(fragments, selector=selector, merge_mode=merge_mode)

            return StreamingResponse(stream(),
                                     media_type="text/event-stream",
                                     headers=SSE_HEADERS)

        rt(route_path)(_handler)

        # ---------- helper that returns the Datastar expression ---------- #
        param_names = list(inspect.signature(func).parameters.keys())[1:]

        def _url(*call_args, _method=method, **call_kwargs):
            qs_dict = {k: v for k, v in zip(param_names, call_args)}
            qs_dict.update(call_kwargs)                          # explicit kwargs
            qs = urllib.parse.urlencode(qs_dict)
            return f"@{_method}('{route_path}?{qs}')" if qs else f"@{_method}('{route_path}')"

        return staticmethod(_url)

    # allow @event *and* @event(method="verb")
    return _decorator if _func is None else _decorator(_func)

class MyState(ReactiveState):
    myInt: int = 0
    myStr: str = "Hello"
    tick_count: int = 0

    @event
    def increment(self, amount: int):
        self.myInt += amount

    @event(method="post")
    def decrement(self, amount: int):
        self.myInt -= amount

    @event(selector="#complex-status-container", merge_mode="inner")
    def start_ticking(self):
        self.tick_count += 1
        return Div(f"Tick #{self.tick_count} - ",Span(data_text="$myInt"))

    @event(selector="#complex-status-container", merge_mode="inner")
    async def start_streaming_ticks(self):
        """Generator that yields fragments over time"""
        async def tick_generator():
            for i in range(10):
                self.tick_count = i+1
                yield H4(f"Stream Tick #{self.tick_count} - ",Span(data_text="$myInt"))
                await asyncio.sleep(0.5)
        return tick_generator()

    @event(selector="#emoji-container", merge_mode="inner")
    async def emoji_generator(self):
        """Generator that yields fragments over time"""
        async def emoji_generator():
            emojis = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊",
                      "🐻", "🐼", "🐨", "🐯", "🦁", "🐮",
                      "🐷", "🐸", "🐵", "🐔", "🐧", "🐦",
                      "🐤", "🐣", "🐥", "🐺", "🦝", "🦄"]
            for emoji in emojis:
                yield H4(f"Hello {emoji}")
                await asyncio.sleep(0.7)
        return emoji_generator()
    
    def __ft__(self):
        return Div(
            H2(self.__class__.__name__, cls="mt-4"),
            Div("$myInt: ",Span(data_text="$myInt"), cls=TextT.extrabold),
            Div("$tick_count: ",Span(data_text="$tick_count"), cls=TextT.extrabold),
            Div("$myStr: ",Span(data_text="$myStr"), cls=TextT.extrabold),
            data_signals=json.dumps(self.model_dump()))

# @rt
# async def tick(request):
#     async def ticks(sse):
#         for i in range(60):
#             yield sse.merge_fragments([Div(f"{[i]}")],
#                                     selector="#complex-status-container",
#                                     merge_mode="inner")
#             await asyncio.sleep(0.5)
#     return DatastarFastHTMLResponse(ticks)

@rt('/')
def index(request):
    state = _get_state(request.session, MyState)
    print(state)
    """Playground page for testing components."""
    return Titled("Component Playground",
        Main(
            Div(data_signals=json.dumps(state.model_dump())),
            Container(
                Section(
                    # CardShowcase(),
                    # Button("Display Charts",data_on_click="@get('/tick')"),
                    Button("Start Ticking", data_on_click=MyState.start_ticking()),
                    Button("Stream Ticks", data_on_click=MyState.start_streaming_ticks()),
                    H1("Counter: ", Span(data_text="$myInt")),
                    Button("+", data_on_click=MyState.increment(1)),
                    Button("-", data_on_click=MyState.decrement(1)),
                    state,

                    H2("State Registry", cls="mt-4"),
                    *[Div(f"{v} : {type(v)}") for k, v in _STATE_REGISTRY.items()],

                    Div(
                        id="complex-status-container",
                        cls="space-y-4 mt-4",
                        # Dynamic fragments will be inserted here
                    ),
                    Button("Emoji", data_on_click=MyState.emoji_generator()),
                    Div(
                        id="emoji-container",
                        cls="space-y-4 mt-4",
                        # Dynamic fragments will be inserted here
                    ),
                    # Div(*[chart for chart in charts],cls="grid grid-cols-2 gap-4", id="charts"),
                    cls="py-10"
                ),
                cls="space-y-4"
            ),
            cls="py-10"
        )
    )
