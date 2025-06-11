from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from pages.templates import page_template

rt = APIRouter()

class LandingState(State):
    """Interactive landing page showcasing StarModel's reactive magic."""
    live_counter: int = 0
    active_connections: int = 1
    lines_written: int = 42
    deploy_status: str = "Ready"
    demo_code: str = """class TodoState(State):
    items: list = []
    count: int = 0
    
    @event
    def add_item(self, text: str):
        self.items.append(text)
        self.count += 1"""
    
    @event
    def pulse_counter(self):
        self.live_counter += 1
        self.active_connections += 1
        self.lines_written += 2
        
    @event
    def simulate_deploy(self):
        self.deploy_status = "Deploying..." if self.deploy_status == "Ready" else "Ready"

@rt('/playground')
@page_template(title="⭐ StarModel - Reactive State Management for Python")
def index(req: Request):
    """Revolutionary landing page showcasing StarModel's reactive magic."""
    state = LandingState.get(req)
    
    return Main(
        state,
        CodeBlock("""
from starmodel import State, event
        """),
        cls="min-h-screen"
    )