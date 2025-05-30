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
from sqlmodel import Field
from faststate.state import event, ReactiveState, _STATE_REGISTRY, _get_state
rt = APIRouter()


class MyState(ReactiveState):
    myInt: int = Field(default=0, title="My Integer", description="An integer value that can be incremented/decremented")
    myStr: str = "Hello"
    tick_count: int = 0

    @event
    def increment(self, amount: int):
        self.myInt += amount

    @event("/decrement",method="post")
    def decrement(self, amount: int):
        self.myInt -= amount

    @event("/reset")
    def reset(self):
        self.myInt = 0

    @event(method="patch")
    def set_myStr(self, value: str):
        self.myStr = value

    @event(selector="#ticker-box", merge_mode="inner")
    def start_ticking(self):
        self.tick_count += 1
        # return Div(f"Tick #{self.tick_count} - ",Span(data_text="$myInt"))
        return H4("Tick actual#",Span(data_text="$tick_count"), cls="text-red-500")

    @event(selector="#ticker-box", merge_mode="inner")
    async def start_streaming_ticks(self):
        """Generator that yields fragments over time"""
        async def tick_generator():
            for i in range(10):
                self.tick_count = i+1
                yield H4(f"Stream Tick# {self.tick_count}", cls="text-red-500")
                await asyncio.sleep(0.5)
        return tick_generator()

    @event(selector="#emoji-container", merge_mode="inner")
    async def emoji_generator(self):
        """Generator that yields fragments over time"""
        async def generator():
            emojis = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊",
                      "🐻", "🐼", "🐨", "🐯", "🦁", "🐮",
                      "🐷", "🐸", "🐵", "🐔", "🐧", "🐦",
                      "🐤", "🐣", "🐥", "🐺", "🦝", "🦄"]
            for emoji in emojis:
                yield H4(f"Hello {emoji}")
                await asyncio.sleep(0.7)
        return generator()
    
    def __ft__(self):
        return Div(
            H2(self.__class__.__name__, cls="mt-4"),
            Div("$myInt: ",Span(data_text="$myInt"), cls=TextT.extrabold),
            Div("$tick_count: ",Span(data_text="$tick_count"), cls=TextT.extrabold),
            Div("$myStr: ",Span(data_text="$myStr"), cls=TextT.extrabold),
            data_signals=json.dumps(self.model_dump()))

@rt('/')
def index(request):
    state = _get_state(request.session, MyState)
    print(state)
    """Playground page for testing components."""
    return Titled("FastState Demo",
        Main(
            Div(data_signals=json.dumps(state.model_dump())),
            state,            
            Input(data_bind="$myStr",data_on_change=MyState.set_myStr(), cls="mt-4"),        
            H1("Counter: ", Span(data_text="$myInt"), cls="mt-4"),
            Div(
                Button("-", data_on_click=MyState.decrement(1)),
                Button("0", data_on_click=MyState.reset()),
                Button("+", data_on_click=MyState.increment(1)),
                cls="mt-2 flex gap-2"
            ),
            Div(
                id="ticker-box",
                cls="space-y-4 mt-4",
                # Dynamic fragments will be inserted here
            ),
            Div(
                Button("Start Ticking", data_on_click=MyState.start_ticking()),
                Button("Stream Ticks", data_on_click=MyState.start_streaming_ticks()),
                cls="mt-2 flex gap-2"
            ),

            H2("State Registry", cls="mt-4"),
            *[Div(f"{v} : {type(v)}") for k, v in _STATE_REGISTRY.items()],

            
            Button("Emoji", data_on_click=MyState.emoji_generator()),
            Div(
                id="emoji-container",
                cls="space-y-4 mt-4",
                # Dynamic fragments will be inserted here
            ),
        ),
        cls="p-10"
    )
