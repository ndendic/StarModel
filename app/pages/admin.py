from fasthtml.common import *
from monsterui.all import *
from faststate import *
import json

rt = APIRouter()

class GlobalSettingsState(State):
    """Global state - shared across all users (admin only)."""
    model_config = {
        "arbitrary_types_allowed": True,
        "faststate_store": StateStore.SERVER_MEMORY,
        "faststate_auto_persist": True,
        "faststate_persistence_backend": memory_persistence,
        "faststate_ttl": None,
    }
    
    theme: str = "light"
    maintenance_mode: bool = False
    announcement: str = ""
    
    @classmethod
    def _generate_state_id(cls, req, **kwargs):
        return "global_settings" 
    
    @event
    def toggle_maintenance(self):
        self.maintenance_mode = not self.maintenance_mode
        status = "enabled" if self.maintenance_mode else "disabled"
        return Div(f"Maintenance mode {status}!", cls="text-orange-600 font-bold")
    
    @event
    def set_announcement(self, announcement: str):
        self.announcement = announcement
        return Div("Announcement updated!", cls="text-blue-600 font-bold")
    
    @event
    def change_theme(self, theme: str):
        self.theme = theme
        return Div(f"Theme changed to {theme}!", cls="text-purple-600 font-bold")


@rt('/admin')
def admin_panel(req: Request):
    """
    Admin panel with global state.
    Uses simple .get() method for state resolution.
    """
    # Simple, explicit state resolution
    settings = GlobalSettingsState.get(req)
    return Titled("Admin Panel",
        Main(
            Div(
                H1("⚙️ Admin Panel", cls="text-3xl font-bold mb-6"),
                
                # Global state display
                Div(data_signals=json.dumps(settings.signals), id="admin-updates"),
                
                # System status
                Div(
                    H2("System Status", cls="text-xl font-bold mb-4"),
                    Div(
                        Div("Theme: ", Span(data_text=GlobalSettingsState.theme), cls="mb-2"),
                        Div("Maintenance Mode: ", Span(data_text=GlobalSettingsState.maintenance_mode), cls="mb-2"),
                        Div("Announcement: ", Span(data_text=GlobalSettingsState.announcement), cls="mb-2"),
                        cls="bg-secondary-foreground p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Admin controls
                Div(
                    H3("Global Controls", cls="text-lg font-bold mb-4"),
                    
                    Div(
                        Button("Toggle Maintenance Mode", 
                               data_on_click=GlobalSettingsState.toggle_maintenance(),
                               cls=ButtonT.primary+"px-4 py-2 rounded mr-2 mb-2"),
                        cls="mb-4"
                    ),
                    
                    Div(
                        Input(placeholder="System announcement...", name="message",
                              data_bind=GlobalSettingsState.announcement,
                              cls="border rounded px-3 py-2 mr-2 flex-1"),
                        Button("Set Announcement", 
                               data_on_click=GlobalSettingsState.set_announcement(),
                               cls=ButtonT.secondary+"px-4 py-2 rounded"),
                        cls="flex mb-4"
                    ),
                    
                    Div(
                        Button("Light Theme", 
                               data_on_click=GlobalSettingsState.change_theme("light"),
                               cls="bg-gray-200 text-gray-800 px-4 py-2 rounded mr-2"),
                        Button("Dark Theme", 
                               data_on_click=GlobalSettingsState.change_theme("dark"),
                               cls="bg-gray-800 text-white px-4 py-2 rounded"),
                        cls="mb-6"
                    ),
                    
                    cls="mb-6"
                ),
                
                # Navigation
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-2xl"
            )
        )
    )

@rt('/status')
def system_status(req: Request):
    """
    System status page showing SSE connections, persistence stats, and more.
    """
    # Get SSE connection stats
    auth = req.session.get("user")
    # Get state cache stats
    from faststate.state import _state_cache
    cached_states = len(_state_cache)
    
    return Titled("System Status",
        Main(
            Div(
                H1("📊 System Status", cls="text-3xl font-bold mb-6"),
                P("Real-time system monitoring and statistics.", 
                  cls="text-gray-600 mb-6"),
                                                
                # State Cache Stats
                Div(
                    H2("State Cache Statistics", cls="text-xl font-bold mb-4"),
                    Div(
                        Div(f"Cached State Instances: {cached_states}", cls="mb-2"),
                        Div("Cache Keys:", cls="mb-2 font-bold"),
                        *[
                            Div(f"  • {cache_key}", cls="ml-4 text-sm text-gray-600")
                            for cache_key in _state_cache.keys()
                        ] if _state_cache else [Div("  • No cached states", cls="ml-4 text-sm text-gray-600")],
                        cls="bg-green-50 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                
                # System Information
                Div(
                    H2("System Information", cls="text-xl font-bold mb-4"),
                    Div(
                        Div(f"Session ID: {req.cookies.get('session_', 'auto-generated')[:100]}", cls="mb-2 font-mono text-sm"),
                        Div(f"Authentication: {auth or 'Not authenticated'}", cls="mb-2 font-mono text-sm"),
                        Div("FastState Version: Enhanced with SSE", cls="mb-2 font-mono text-sm"),
                        cls="bg-gray-50 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Test SSE Connection
                Div(
                    H2("Test SSE Connection", cls="text-xl font-bold mb-4"),
                    Div(
                        Button("Connect to Global SSE", 
                               onclick="connectToSSE()",
                               cls="bg-blue-500 text-white px-4 py-2 rounded mr-2"),
                        Button("Disconnect SSE", 
                               onclick="disconnectSSE()",
                               cls="bg-red-500 text-white px-4 py-2 rounded"),
                        Div(id="sse-status", cls="mt-4 p-3 rounded bg-gray-100"),
                        cls="mb-6"
                    ),
                    
                    Script("""
                        let eventSource = null;
                        
                        function connectToSSE() {
                            if (eventSource) {
                                eventSource.close();
                            }
                            
                            eventSource = new EventSource('/faststate/sse?states=CounterState,ChatState');
                            document.getElementById('sse-status').innerHTML = 'Connecting to SSE...';
                            
                            eventSource.onopen = function() {
                                document.getElementById('sse-status').innerHTML = 
                                    '<span class="text-green-600">✅ Connected to SSE stream</span>';
                            };
                            
                            eventSource.onmessage = function(event) {
                                const status = document.getElementById('sse-status');
                                status.innerHTML = 
                                    '<span class="text-blue-600">📡 Received: </span>' + 
                                    '<code class="text-sm">' + event.data.substring(0, 100) + '...</code>';
                            };
                            
                            eventSource.onerror = function() {
                                document.getElementById('sse-status').innerHTML = 
                                    '<span class="text-red-600">❌ SSE connection error</span>';
                            };
                        }
                        
                        function disconnectSSE() {
                            if (eventSource) {
                                eventSource.close();
                                eventSource = null;
                                document.getElementById('sse-status').innerHTML = 
                                    '<span class="text-gray-600">Disconnected from SSE</span>';
                            }
                        }
                    """),
                    cls="mb-6"
                ),
                
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-4xl"
            )
        )
    )


