from fasthtml.common import *
from monsterui.all import *
from faststate import *

rt = APIRouter()

conf = StateConfig(
    scope=StateScope.GLOBAL,
    auto_persist=True,
    persistence_backend="memory",
    ttl=None
)

class ChatState(State):
    """Global chat state for real-time collaboration demo."""
    messages: list = []
    active_users: int = 0
    last_message_id: int = 0
    
    # Auto-registration configuration
    _config = conf
    
    @event(selector="#chat-messages",  merge_mode="append")
    def send_message(self, username: str, message: str):
        if not message.strip():
            return Div("Message cannot be empty", cls="text-red-500")
        
        self.last_message_id += 1
        new_message = {
            "id": self.last_message_id,
            "username": username or "Anonymous",
            "message": message.strip(),
            "timestamp": "now"
        }
        
        # Keep only last 10 messages for demo
        if len(self.messages) >= 10:
            self.messages = self.messages[-9:]
        self.messages.append(new_message)
        
        return Div(
            Div(
                Span(new_message["username"], cls="font-bold text-blue-600"),
                Span(f" ({new_message['timestamp']})", cls="text-xs text-gray-500 ml-2"),
                cls="mb-1"
            ),
            Div(new_message["message"], cls="text-gray-800"),
            cls="bg-blue-50 p-3 rounded mb-2 border-l-4 border-blue-500"
        )
    
    @event
    def join_chat(self, username: str):
        self.active_users += 1
        return Div(f"{username} joined the chat!", cls="text-green-600 font-bold")
    
    @event
    def leave_chat(self, username: str):
        if self.active_users > 0:
            self.active_users -= 1
        return Div(f"{username} left the chat.", cls="text-orange-600")
    

@rt('/chat')
def realtime_chat(req: Request, sess: dict, auth: str = None):
    """
    Real-time chat demo showcasing global state and SSE broadcasting.
    """
    chat = ChatState.get(req, sess, auth)
    username = auth or sess.get('auth', 'Anonymous')
    
    return Titled("Real-time Chat",
        Main(
            Div(
                H1("💬 Real-time Chat Demo", cls="text-3xl font-bold mb-6"),
                P("This demonstrates global state with real-time SSE broadcasting across all connected users.", 
                  cls=TextPresets.muted_sm+"mb-6"),
                
                # Chat state display
                chat,
                chat.LiveDiv(heartbeat=0),
                
                # Chat info
                Div(
                    H2("Chat Status", cls="text-xl font-bold mb-4"),
                    Div(
                        Div("Active Users: ", Span(data_text="$active_users"), cls="mb-2"),
                        Div("Total Messages: ", Span(str(len(chat.messages))), cls="mb-2"),
                        Div(f"Your Username: {username}", cls="mb-2 font-mono"),
                        cls="bg-gray-100 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Chat messages area
                Div(
                    H3("Messages", cls="text-lg font-bold mb-4"),
                    Div(
                        *[
                            Div(
                                Div(
                                    Span(msg["username"], cls="font-bold text-blue-600"),
                                    Span(f" ({msg['timestamp']})", cls="text-xs text-gray-500 ml-2"),
                                    cls="mb-1"
                                ),
                                Div(msg["message"], cls="text-gray-800"),
                                cls="bg-blue-50 p-3 rounded mb-2 border-l-4 border-blue-500"
                            ) for msg in chat.messages
                        ],
                        id="chat-messages",
                        cls="h-64 overflow-y-auto bg-white border rounded p-4 mb-4"
                    ),
                    cls="mb-6"
                ),
                
                # Chat input
                Div(
                    H3("Send Message", cls="text-lg font-bold mb-4"),
                    Form(
                        Input(value=username, data_bind="$username", placeholder="Username", 
                              cls="border rounded px-3 py-2 mr-2 w-32"),
                        Input(data_bind="$message", placeholder="Type your message...", 
                              cls="border rounded px-3 py-2 mr-2 flex-1"),
                        Button("Send", type="submit", 
                               cls="bg-blue-500 text-white px-6 py-2 rounded"),
                        data_on_submit=ChatState.send_message(),
                        cls="flex mb-4"
                    ),
                    cls="mb-6"
                ),
                
                # Chat actions
                Div(
                    Button("Join Chat", 
                           data_on_click=ChatState.join_chat(username),
                           cls="bg-green-500 text-white px-4 py-2 rounded mr-2"),
                    Button("Leave Chat", 
                           data_on_click=ChatState.leave_chat(username),
                           cls="bg-red-500 text-white px-4 py-2 rounded"),
                    cls="mb-6"
                ),
                
                A("← Back to Home", href="/", cls="text-blue-500 hover:underline"),
                
                cls="container mx-auto p-8 max-w-4xl"
            )
        )
    )
