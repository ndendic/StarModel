"""
Web Interfaces - Framework-Agnostic Web Abstractions

🌐 Clean Web Contract:
This module defines the core interfaces for web interactions, providing
a clean abstraction layer that keeps domain logic independent of any
specific web framework (FastHTML, FastAPI, Django, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

class HttpMethod(Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

class ContentType(Enum):
    """Common content types"""
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
    FORM = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"
    XML = "application/xml"
    STREAM = "text/event-stream"

@dataclass
class WebCookie:
    """Web cookie representation"""
    name: str
    value: str
    max_age: Optional[int] = None
    expires: Optional[datetime] = None
    path: str = "/"
    domain: Optional[str] = None
    secure: bool = False
    http_only: bool = True
    same_site: Optional[str] = "lax"

@dataclass
class WebFile:
    """Uploaded file representation"""
    filename: str
    content_type: str
    size: int
    content: bytes

class WebRequest(ABC):
    """
    Abstract web request interface.
    
    Provides framework-agnostic access to HTTP request data,
    allowing domain logic to work with any web framework.
    """
    
    @property
    @abstractmethod
    def method(self) -> HttpMethod:
        """Get HTTP method"""
        pass
    
    @property
    @abstractmethod
    def url(self) -> str:
        """Get full request URL"""
        pass
    
    @property
    @abstractmethod
    def path(self) -> str:
        """Get request path"""
        pass
    
    @property
    @abstractmethod
    def query_params(self) -> Dict[str, str]:
        """Get query parameters"""
        pass
    
    @property
    @abstractmethod
    def headers(self) -> Dict[str, str]:
        """Get request headers"""
        pass
    
    @property
    @abstractmethod
    def cookies(self) -> Dict[str, str]:
        """Get request cookies"""
        pass
    
    @abstractmethod
    async def body(self) -> bytes:
        """Get raw request body"""
        pass
    
    @abstractmethod
    async def text(self) -> str:
        """Get request body as text"""
        pass
    
    @abstractmethod
    async def json(self) -> Dict[str, Any]:
        """Get request body as JSON"""
        pass
    
    @abstractmethod
    async def form(self) -> Dict[str, Union[str, List[str]]]:
        """Get form data"""
        pass
    
    @abstractmethod
    async def files(self) -> Dict[str, WebFile]:
        """Get uploaded files"""
        pass
    
    @property
    @abstractmethod
    def content_type(self) -> Optional[str]:
        """Get content type"""
        pass
    
    @property
    @abstractmethod
    def client_ip(self) -> Optional[str]:
        """Get client IP address"""
        pass
    
    @property
    @abstractmethod
    def user_agent(self) -> Optional[str]:
        """Get user agent"""
        pass
    
    # Session and authentication
    @abstractmethod
    def get_session(self) -> Dict[str, Any]:
        """Get session data"""
        pass
    
    @abstractmethod
    def set_session(self, key: str, value: Any):
        """Set session data"""
        pass
    
    @abstractmethod
    def get_user(self) -> Optional[Any]:
        """Get authenticated user"""
        pass
    
    # StarModel-specific methods
    @abstractmethod
    def get_datastar_payload(self) -> Dict[str, Any]:
        """Get Datastar payload from request"""
        pass
    
    @abstractmethod
    def get_entity_id(self, entity_class: type) -> Optional[str]:
        """Extract entity ID from request"""
        pass

class WebResponse(ABC):
    """
    Abstract web response interface.
    
    Provides framework-agnostic response building,
    allowing domain logic to construct responses without
    depending on specific web framework response objects.
    """
    
    def __init__(self):
        self._status_code: int = 200
        self._headers: Dict[str, str] = {}
        self._cookies: List[WebCookie] = []
        self._content: Optional[bytes] = None
        self._content_type: str = ContentType.HTML.value
    
    @property
    def status_code(self) -> int:
        """Get HTTP status code"""
        return self._status_code
    
    @status_code.setter
    def status_code(self, value: int):
        """Set HTTP status code"""
        self._status_code = value
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get response headers"""
        return self._headers
    
    @property
    def cookies(self) -> List[WebCookie]:
        """Get response cookies"""
        return self._cookies
    
    @property
    def content_type(self) -> str:
        """Get content type"""
        return self._content_type
    
    @content_type.setter
    def content_type(self, value: str):
        """Set content type"""
        self._content_type = value
        self._headers["Content-Type"] = value
    
    def set_header(self, name: str, value: str):
        """Set response header"""
        self._headers[name] = value
    
    def add_cookie(self, cookie: WebCookie):
        """Add response cookie"""
        self._cookies.append(cookie)
    
    def set_cookie(self, name: str, value: str, **kwargs):
        """Set cookie with options"""
        cookie = WebCookie(name=name, value=value, **kwargs)
        self.add_cookie(cookie)
    
    @abstractmethod
    def set_content(self, content: Union[str, bytes, Dict[str, Any]]):
        """Set response content"""
        pass
    
    @abstractmethod
    def set_json(self, data: Dict[str, Any]):
        """Set JSON response"""
        pass
    
    @abstractmethod
    def set_html(self, html: str):
        """Set HTML response"""
        pass
    
    @abstractmethod
    def set_text(self, text: str):
        """Set plain text response"""
        pass
    
    @abstractmethod
    def set_redirect(self, url: str, status_code: int = 302):
        """Set redirect response"""
        pass
    
    @abstractmethod
    def set_stream(self, generator: AsyncIterator[str]):
        """Set streaming response"""
        pass
    
    # StarModel-specific methods
    @abstractmethod
    def set_sse_response(self, data: Dict[str, Any]):
        """Set Server-Sent Events response"""
        pass
    
    @abstractmethod
    def set_datastar_response(self, signals: Dict[str, Any], fragments: Optional[str] = None):
        """Set Datastar response with signals and fragments"""
        pass

class RouteHandler(ABC):
    """
    Abstract route handler interface.
    
    Defines the contract for handling web requests
    in a framework-agnostic way.
    """
    
    @abstractmethod
    async def handle(self, request: WebRequest) -> WebResponse:
        """Handle web request and return response"""
        pass

class WebAdapter(ABC):
    """
    Abstract web framework adapter.
    
    Provides the interface for integrating StarModel
    with different web frameworks (FastHTML, FastAPI, etc.).
    """
    
    @abstractmethod
    def create_request(self, framework_request: Any) -> WebRequest:
        """Create WebRequest from framework-specific request"""
        pass
    
    @abstractmethod
    def create_response(self) -> WebResponse:
        """Create WebResponse instance"""
        pass
    
    @abstractmethod
    async def send_response(self, response: WebResponse, framework_response: Any):
        """Send WebResponse using framework-specific response"""
        pass
    
    @abstractmethod
    def register_route(self, method: HttpMethod, path: str, handler: RouteHandler):
        """Register route with the web framework"""
        pass
    
    @abstractmethod
    def register_middleware(self, middleware: Callable):
        """Register middleware with the web framework"""
        pass
    
    @abstractmethod
    def start_server(self, host: str = "localhost", port: int = 8000):
        """Start the web server"""
        pass
    
    @abstractmethod
    def stop_server(self):
        """Stop the web server"""
        pass

class WebContext:
    """
    Web context for request processing.
    
    Provides additional context information during
    request processing, including dependency injection
    container and application state.
    """
    
    def __init__(self, request: WebRequest, adapter: WebAdapter):
        self.request = request
        self.adapter = adapter
        self.container = None  # Will be injected
        self.session_data: Dict[str, Any] = {}
        self.user = None
        self.start_time = datetime.now()
    
    def get_service(self, service_type: type):
        """Get service from DI container"""
        if self.container:
            return self.container.get(service_type)
        return None
    
    def get_entity_repository(self, entity_class: type):
        """Get repository for entity class"""
        persistence_manager = self.get_service("PersistenceManager")
        if persistence_manager:
            import asyncio
            return asyncio.run(persistence_manager.get_repository(entity_class))
        return None
    
    def get_event_dispatcher(self):
        """Get event dispatcher"""
        return self.get_service("EventDispatcher")

# Response builders for common patterns
class ResponseBuilder:
    """Helper class for building common response types"""
    
    @staticmethod
    def ok(content: str = "OK") -> Dict[str, Any]:
        """Build 200 OK response"""
        return {"status_code": 200, "content": content}
    
    @staticmethod
    def created(content: str = "Created") -> Dict[str, Any]:
        """Build 201 Created response"""
        return {"status_code": 201, "content": content}
    
    @staticmethod
    def bad_request(message: str = "Bad Request") -> Dict[str, Any]:
        """Build 400 Bad Request response"""
        return {"status_code": 400, "content": message}
    
    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> Dict[str, Any]:
        """Build 401 Unauthorized response"""
        return {"status_code": 401, "content": message}
    
    @staticmethod
    def forbidden(message: str = "Forbidden") -> Dict[str, Any]:
        """Build 403 Forbidden response"""
        return {"status_code": 403, "content": message}
    
    @staticmethod
    def not_found(message: str = "Not Found") -> Dict[str, Any]:
        """Build 404 Not Found response"""
        return {"status_code": 404, "content": message}
    
    @staticmethod
    def internal_error(message: str = "Internal Server Error") -> Dict[str, Any]:
        """Build 500 Internal Server Error response"""
        return {"status_code": 500, "content": message}
    
    @staticmethod
    def json_response(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
        """Build JSON response"""
        return {
            "status_code": status_code,
            "content": json.dumps(data),
            "content_type": ContentType.JSON.value
        }
    
    @staticmethod
    def sse_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Build Server-Sent Events response"""
        sse_data = f"data: {json.dumps(data)}\n\n"
        return {
            "status_code": 200,
            "content": sse_data,
            "content_type": ContentType.STREAM.value,
            "headers": {
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        }

# Export main components
__all__ = [
    "WebRequest", "WebResponse", "RouteHandler", "WebAdapter", "WebContext",
    "HttpMethod", "ContentType", "WebCookie", "WebFile",
    "ResponseBuilder"
]