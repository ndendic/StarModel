"""
Response Formatters - Pluggable Real-time Response Formatting

⚡ Pluggable Response Formatting:
This module provides pluggable response formatters for different real-time mechanisms,
enabling clean separation between command results and response format specifics.

Key Features:
- Abstract formatter interface for pluggability
- Datastar SSE formatter for real-time UI updates
- JSON formatter for API responses
- WebSocket formatter for bidirectional communication
- Template-based HTML formatters
"""

import json
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncIterator, List, Union
from dataclasses import dataclass
from datetime import datetime

from ...events.dispatching.command_context import CommandResult
from ...infrastructure.web.interfaces import WebRequest, WebResponse, ContentType

@dataclass
class FormatterContext:
    """Context information for response formatting"""
    request: Optional[WebRequest]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    client_capabilities: Dict[str, Any] = None
    format_preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.client_capabilities is None:
            self.client_capabilities = {}
        if self.format_preferences is None:
            self.format_preferences = {}

class ResponseFormatter(ABC):
    """
    Abstract response formatter interface.
    
    Provides the contract for formatting command results into
    web responses for different real-time mechanisms and protocols.
    """
    
    @abstractmethod
    async def format_response(
        self, 
        result: CommandResult, 
        context: FormatterContext
    ) -> WebResponse:
        """
        Format command result for client consumption.
        
        Args:
            result: Command execution result
            context: Formatting context with request info
            
        Returns:
            Formatted web response
        """
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if this formatter supports streaming responses"""
        pass
    
    @abstractmethod
    def get_content_type(self) -> str:
        """Get the content type this formatter produces"""
        pass

class DatastarSSEFormatter(ResponseFormatter):
    """
    Datastar Server-Sent Events formatter.
    
    Formats command results as SSE streams with Datastar-compatible
    signal updates and HTML fragment merging.
    """
    
    def __init__(self, include_debug_info: bool = False):
        self.include_debug_info = include_debug_info
    
    async def format_response(
        self, 
        result: CommandResult, 
        context: FormatterContext
    ) -> WebResponse:
        """Format as Datastar SSE stream"""
        
        async def generate_sse_events():
            """Generate SSE events from command result"""
            
            # Send signals update if available
            if result.signals_updated:
                signal_data = {
                    "type": "signals",
                    "data": result.signals_updated,
                    "timestamp": datetime.now().isoformat()
                }
                
                if self.include_debug_info:
                    signal_data["debug"] = {
                        "command_id": result.command_id,
                        "execution_time_ms": result.execution_time_ms
                    }
                
                yield f"event: datastar-signal\n"
                yield f"data: {json.dumps(signal_data)}\n\n"
            
            # Send fragments if available
            for i, fragment in enumerate(result.fragments_generated):
                fragment_data = {
                    "type": "fragment",
                    "selector": result.get_response_hint("selector", f"#fragment-{i}"),
                    "merge": result.get_response_hint("merge_mode", "morph"),
                    "data": self._serialize_fragment(fragment),
                    "timestamp": datetime.now().isoformat()
                }
                
                if self.include_debug_info:
                    fragment_data["debug"] = {
                        "fragment_index": i,
                        "fragment_type": type(fragment).__name__
                    }
                
                yield f"event: datastar-fragment\n"
                yield f"data: {json.dumps(fragment_data)}\n\n"
            
            # Send completion event
            completion_data = {
                "type": "complete",
                "success": result.success,
                "timestamp": datetime.now().isoformat()
            }
            
            if not result.success and result.error_message:
                completion_data["error"] = {
                    "message": result.error_message,
                    "code": result.error_code
                }
            
            if self.include_debug_info:
                completion_data["debug"] = {
                    "command_id": result.command_id,
                    "execution_time_ms": result.execution_time_ms,
                    "events_published": len(result.events_published)
                }
            
            yield f"event: datastar-complete\n"
            yield f"data: {json.dumps(completion_data)}\n\n"
        
        # Create streaming response
        from ...infrastructure.web.interfaces import WebResponse
        
        # Create a concrete response implementation
        response = DatastarSSEResponse()
        response.set_stream(generate_sse_events())
        response.content_type = ContentType.STREAM.value
        response.set_header("Cache-Control", "no-cache")
        response.set_header("Connection", "keep-alive")
        response.set_header("X-Accel-Buffering", "no")  # Disable nginx buffering
        
        return response
    
    def supports_streaming(self) -> bool:
        """Datastar SSE supports streaming"""
        return True
    
    def get_content_type(self) -> str:
        """SSE content type"""
        return ContentType.STREAM.value
    
    def _serialize_fragment(self, fragment: Any) -> str:
        """Serialize fragment for transmission"""
        if hasattr(fragment, 'render'):
            # FastHTML component
            return fragment.render()
        elif hasattr(fragment, '__html__'):
            # HTML-like object
            return fragment.__html__()
        elif isinstance(fragment, str):
            # Plain string
            return fragment
        else:
            # Convert to string
            return str(fragment)

class JSONResponseFormatter(ResponseFormatter):
    """
    JSON response formatter.
    
    Formats command results as structured JSON responses
    suitable for API consumption and non-real-time clients.
    """
    
    def __init__(self, include_metadata: bool = True):
        self.include_metadata = include_metadata
    
    async def format_response(
        self, 
        result: CommandResult, 
        context: FormatterContext
    ) -> WebResponse:
        """Format as JSON response"""
        
        response_data = {
            "success": result.success,
            "data": {
                "signals": result.signals_updated,
                "fragments": [str(f) for f in result.fragments_generated],
                "return_value": self._serialize_return_value(result.return_value)
            }
        }
        
        if not result.success:
            response_data["error"] = {
                "message": result.error_message,
                "code": result.error_code
            }
        
        if self.include_metadata:
            response_data["metadata"] = {
                "command_id": result.command_id,
                "execution_time_ms": result.execution_time_ms,
                "events_published": result.events_published,
                "timestamp": datetime.now().isoformat()
            }
        
        # Create JSON response
        response = JSONWebResponse()
        response.set_json(response_data)
        response.status_code = 200 if result.success else 400
        
        return response
    
    def supports_streaming(self) -> bool:
        """JSON doesn't support streaming"""
        return False
    
    def get_content_type(self) -> str:
        """JSON content type"""
        return ContentType.JSON.value
    
    def _serialize_return_value(self, value: Any) -> Any:
        """Serialize return value for JSON transmission"""
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool, list, dict)):
            return value
        elif hasattr(value, 'model_dump'):
            # Pydantic model
            return value.model_dump()
        elif hasattr(value, '__dict__'):
            # Object with attributes
            return {k: v for k, v in value.__dict__.items() if not k.startswith('_')}
        else:
            return str(value)

class WebSocketFormatter(ResponseFormatter):
    """
    WebSocket response formatter.
    
    Formats command results for WebSocket transmission,
    enabling bidirectional real-time communication.
    """
    
    def __init__(self, message_type: str = "command_result"):
        self.message_type = message_type
    
    async def format_response(
        self, 
        result: CommandResult, 
        context: FormatterContext
    ) -> WebResponse:
        """Format for WebSocket transmission"""
        
        message = {
            "type": self.message_type,
            "id": result.command_id,
            "success": result.success,
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "signals": result.signals_updated,
                "fragments": [str(f) for f in result.fragments_generated],
                "events": result.events_published
            }
        }
        
        if not result.success:
            message["error"] = {
                "message": result.error_message,
                "code": result.error_code
            }
        
        # Create WebSocket response
        response = WebSocketResponse()
        response.set_json(message)
        
        return response
    
    def supports_streaming(self) -> bool:
        """WebSocket supports streaming"""
        return True
    
    def get_content_type(self) -> str:
        """WebSocket content type"""
        return "application/json"

class HTMLTemplateFormatter(ResponseFormatter):
    """
    HTML template formatter.
    
    Formats command results using HTML templates,
    suitable for traditional web applications.
    """
    
    def __init__(self, template_engine=None):
        self.template_engine = template_engine
    
    async def format_response(
        self, 
        result: CommandResult, 
        context: FormatterContext
    ) -> WebResponse:
        """Format using HTML templates"""
        
        # Simple HTML formatting without template engine
        if result.success:
            html_content = self._generate_success_html(result)
        else:
            html_content = self._generate_error_html(result)
        
        response = HTMLWebResponse()
        response.set_html(html_content)
        
        return response
    
    def supports_streaming(self) -> bool:
        """HTML doesn't support streaming by default"""
        return False
    
    def get_content_type(self) -> str:
        """HTML content type"""
        return ContentType.HTML.value
    
    def _generate_success_html(self, result: CommandResult) -> str:
        """Generate HTML for successful result"""
        fragments_html = "".join(str(f) for f in result.fragments_generated)
        
        return f"""
        <div class="command-result success" data-command-id="{result.command_id}">
            <div class="fragments">{fragments_html}</div>
            <script>
                // Update signals
                if (window.datastar) {{
                    window.datastar.mergeSignals({json.dumps(result.signals_updated)});
                }}
            </script>
        </div>
        """
    
    def _generate_error_html(self, result: CommandResult) -> str:
        """Generate HTML for error result"""
        return f"""
        <div class="command-result error" data-command-id="{result.command_id}">
            <div class="error-message">{result.error_message}</div>
            <div class="error-code">{result.error_code}</div>
        </div>
        """

# Concrete response implementations for different formatters
class DatastarSSEResponse(WebResponse):
    """Concrete SSE response for Datastar"""
    
    def __init__(self):
        super().__init__()
        self._streaming_generator = None
    
    def set_content(self, content: Union[str, bytes, Dict[str, Any]]):
        if isinstance(content, dict):
            self.set_json(content)
        else:
            self._content = str(content).encode('utf-8') if isinstance(content, str) else content
    
    def set_json(self, data: Dict[str, Any]):
        self._content = json.dumps(data).encode('utf-8')
    
    def set_html(self, html: str):
        self._content = html.encode('utf-8')
    
    def set_text(self, text: str):
        self._content = text.encode('utf-8')
    
    def set_redirect(self, url: str, status_code: int = 302):
        self.status_code = status_code
        self.set_header('Location', url)
    
    def set_stream(self, generator: AsyncIterator[str]):
        self._streaming_generator = generator
    
    def set_sse_response(self, data: Dict[str, Any]):
        sse_data = f"data: {json.dumps(data)}\n\n"
        self.set_content(sse_data)
    
    def set_datastar_response(self, signals: Dict[str, Any], fragments: Optional[str] = None):
        if fragments:
            self.set_html(fragments)
            self.set_header('X-Datastar-Signals', json.dumps(signals))
        else:
            self.set_sse_response(signals)

class JSONWebResponse(WebResponse):
    """Concrete JSON response"""
    
    def set_content(self, content: Union[str, bytes, Dict[str, Any]]):
        if isinstance(content, dict):
            self.set_json(content)
        else:
            self._content = str(content).encode('utf-8') if isinstance(content, str) else content
    
    def set_json(self, data: Dict[str, Any]):
        self._content = json.dumps(data).encode('utf-8')
        self.content_type = ContentType.JSON.value
    
    def set_html(self, html: str):
        self._content = html.encode('utf-8')
        self.content_type = ContentType.HTML.value
    
    def set_text(self, text: str):
        self._content = text.encode('utf-8')
        self.content_type = ContentType.TEXT.value
    
    def set_redirect(self, url: str, status_code: int = 302):
        self.status_code = status_code
        self.set_header('Location', url)
    
    def set_stream(self, generator: AsyncIterator[str]):
        # JSON responses don't support streaming
        pass
    
    def set_sse_response(self, data: Dict[str, Any]):
        self.set_json(data)
    
    def set_datastar_response(self, signals: Dict[str, Any], fragments: Optional[str] = None):
        response_data = {"signals": signals}
        if fragments:
            response_data["fragments"] = fragments
        self.set_json(response_data)

class WebSocketResponse(WebResponse):
    """Concrete WebSocket response"""
    
    def set_content(self, content: Union[str, bytes, Dict[str, Any]]):
        if isinstance(content, dict):
            self.set_json(content)
        else:
            self._content = str(content).encode('utf-8') if isinstance(content, str) else content
    
    def set_json(self, data: Dict[str, Any]):
        self._content = json.dumps(data).encode('utf-8')
    
    def set_html(self, html: str):
        self._content = html.encode('utf-8')
    
    def set_text(self, text: str):
        self._content = text.encode('utf-8')
    
    def set_redirect(self, url: str, status_code: int = 302):
        # WebSocket doesn't support redirects
        pass
    
    def set_stream(self, generator: AsyncIterator[str]):
        # WebSocket handles streaming differently
        pass
    
    def set_sse_response(self, data: Dict[str, Any]):
        self.set_json(data)
    
    def set_datastar_response(self, signals: Dict[str, Any], fragments: Optional[str] = None):
        response_data = {"signals": signals}
        if fragments:
            response_data["fragments"] = fragments
        self.set_json(response_data)

class HTMLWebResponse(WebResponse):
    """Concrete HTML response"""
    
    def set_content(self, content: Union[str, bytes, Dict[str, Any]]):
        if isinstance(content, dict):
            # Convert dict to JSON and embed in HTML
            json_str = json.dumps(content)
            html = f"<script>window.data = {json_str};</script>"
            self._content = html.encode('utf-8')
        else:
            self._content = str(content).encode('utf-8') if isinstance(content, str) else content
    
    def set_json(self, data: Dict[str, Any]):
        # Embed JSON in HTML
        json_str = json.dumps(data)
        html = f"<script>window.data = {json_str};</script>"
        self._content = html.encode('utf-8')
    
    def set_html(self, html: str):
        self._content = html.encode('utf-8')
        self.content_type = ContentType.HTML.value
    
    def set_text(self, text: str):
        # Wrap text in HTML
        html = f"<pre>{text}</pre>"
        self._content = html.encode('utf-8')
        self.content_type = ContentType.HTML.value
    
    def set_redirect(self, url: str, status_code: int = 302):
        self.status_code = status_code
        self.set_header('Location', url)
    
    def set_stream(self, generator: AsyncIterator[str]):
        # HTML doesn't support streaming by default
        pass
    
    def set_sse_response(self, data: Dict[str, Any]):
        # Convert SSE to HTML
        html = f"<div class='sse-data'>{json.dumps(data)}</div>"
        self.set_html(html)
    
    def set_datastar_response(self, signals: Dict[str, Any], fragments: Optional[str] = None):
        html_parts = []
        if fragments:
            html_parts.append(fragments)
        html_parts.append(f"<script>if (window.datastar) {{ window.datastar.mergeSignals({json.dumps(signals)}); }}</script>")
        self.set_html("".join(html_parts))

# Formatter registry for easy selection
class FormatterRegistry:
    """Registry for response formatters"""
    
    def __init__(self):
        self._formatters: Dict[str, ResponseFormatter] = {}
        self._setup_default_formatters()
    
    def _setup_default_formatters(self):
        """Set up default formatters"""
        self.register("datastar-sse", DatastarSSEFormatter())
        self.register("json", JSONResponseFormatter())
        self.register("websocket", WebSocketFormatter())
        self.register("html", HTMLTemplateFormatter())
    
    def register(self, name: str, formatter: ResponseFormatter):
        """Register a formatter"""
        self._formatters[name] = formatter
    
    def get(self, name: str) -> Optional[ResponseFormatter]:
        """Get a formatter by name"""
        return self._formatters.get(name)
    
    def get_for_request(self, request: WebRequest) -> ResponseFormatter:
        """Get best formatter for request"""
        # Check Accept header
        accept_header = request.headers.get('accept', '')
        
        if 'text/event-stream' in accept_header:
            return self.get("datastar-sse")
        elif 'application/json' in accept_header:
            return self.get("json")
        elif 'text/html' in accept_header:
            return self.get("html")
        else:
            # Default to JSON
            return self.get("json")

# Global formatter registry
_formatter_registry = FormatterRegistry()

def get_formatter_registry() -> FormatterRegistry:
    """Get the global formatter registry"""
    return _formatter_registry

def get_formatter(name: str) -> Optional[ResponseFormatter]:
    """Get a formatter by name"""
    return _formatter_registry.get(name)

# Export main components
__all__ = [
    "ResponseFormatter", "FormatterContext", "FormatterRegistry",
    "DatastarSSEFormatter", "JSONResponseFormatter", "WebSocketFormatter", "HTMLTemplateFormatter",
    "get_formatter_registry", "get_formatter"
]