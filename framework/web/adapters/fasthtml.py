"""
FastHTML Web Adapter - FastHTML Framework Integration

⚡ FastHTML Clean Integration:
This module provides a clean adapter for integrating StarModel with
the FastHTML web framework, maintaining separation between domain
logic and web framework specifics.
"""

from typing import Any, Dict, List, Optional, Union, AsyncIterator
import json
import asyncio
from datetime import datetime

try:
    from fasthtml.common import *
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import Response as StarletteResponse, StreamingResponse
    FASTHTML_AVAILABLE = True
except ImportError:
    # Graceful fallback when FastHTML is not available
    FASTHTML_AVAILABLE = False
    StarletteRequest = object
    StarletteResponse = object
    StreamingResponse = object

from ..interfaces import (
    WebRequest, WebResponse, WebAdapter, RouteHandler, WebContext,
    HttpMethod, ContentType, WebCookie, WebFile, ResponseBuilder
)
from ..routing import RouteRegistry, Route, RouteMethod
from ..session import SessionManager, SessionData

class FastHTMLRequest(WebRequest):
    """FastHTML-specific WebRequest implementation"""
    
    def __init__(self, fasthtml_request: StarletteRequest, session_data: Optional[SessionData] = None):
        if not FASTHTML_AVAILABLE:
            raise ImportError("FastHTML is not available. Please install fasthtml to use FastHTMLAdapter.")
        
        self._request = fasthtml_request
        self._session_data = session_data
        self._cached_body = None
        self._cached_json = None
        self._cached_form = None
    
    @property
    def method(self) -> HttpMethod:
        """Get HTTP method"""
        return HttpMethod(self._request.method.upper())
    
    @property
    def url(self) -> str:
        """Get full request URL"""
        return str(self._request.url)
    
    @property
    def path(self) -> str:
        """Get request path"""
        return self._request.url.path
    
    @property
    def query_params(self) -> Dict[str, str]:
        """Get query parameters"""
        return dict(self._request.query_params)
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers"""
        return dict(self._request.headers)
    
    @property
    def cookies(self) -> Dict[str, str]:
        """Get request cookies"""
        return dict(self._request.cookies)
    
    async def body(self) -> bytes:
        """Get raw request body"""
        if self._cached_body is None:
            self._cached_body = await self._request.body()
        return self._cached_body
    
    async def text(self) -> str:
        """Get request body as text"""
        body = await self.body()
        return body.decode('utf-8')
    
    async def json(self) -> Dict[str, Any]:
        """Get request body as JSON"""
        if self._cached_json is None:
            text = await self.text()
            try:
                self._cached_json = json.loads(text) if text else {}
            except json.JSONDecodeError:
                self._cached_json = {}
        return self._cached_json
    
    async def form(self) -> Dict[str, Union[str, List[str]]]:
        """Get form data"""
        if self._cached_form is None:
            form_data = await self._request.form()
            self._cached_form = {}
            
            for key, value in form_data.items():
                if key in self._cached_form:
                    # Handle multiple values for same key
                    if isinstance(self._cached_form[key], list):
                        self._cached_form[key].append(value)
                    else:
                        self._cached_form[key] = [self._cached_form[key], value]
                else:
                    self._cached_form[key] = value
        
        return self._cached_form
    
    async def files(self) -> Dict[str, WebFile]:
        """Get uploaded files"""
        form_data = await self._request.form()
        files = {}
        
        for key, file_upload in form_data.items():
            if hasattr(file_upload, 'filename') and hasattr(file_upload, 'content_type'):
                # This is a file upload
                content = await file_upload.read() if hasattr(file_upload, 'read') else b''
                files[key] = WebFile(
                    filename=file_upload.filename or '',
                    content_type=file_upload.content_type or 'application/octet-stream',
                    size=len(content),
                    content=content
                )
        
        return files
    
    @property
    def content_type(self) -> Optional[str]:
        """Get content type"""
        return self._request.headers.get('content-type')
    
    @property
    def client_ip(self) -> Optional[str]:
        """Get client IP address"""
        return self._request.client.host if self._request.client else None
    
    @property
    def user_agent(self) -> Optional[str]:
        """Get user agent"""
        return self._request.headers.get('user-agent')
    
    # Session and authentication
    def get_session(self) -> Dict[str, Any]:
        """Get session data"""
        return self._session_data.data if self._session_data else {}
    
    def set_session(self, key: str, value: Any):
        """Set session data"""
        if self._session_data:
            self._session_data.set(key, value)
    
    def get_user(self) -> Optional[Any]:
        """Get authenticated user"""
        if self._session_data and self._session_data.is_authenticated:
            return self._session_data.user_id
        return None
    
    # StarModel-specific methods
    def get_datastar_payload(self) -> Dict[str, Any]:
        """Get Datastar payload from request"""
        # Datastar sends data as form data or query params
        payload = {}
        
        # Try query params first
        for key, value in self.query_params.items():
            if key.startswith('$'):
                # This is a signal value
                try:
                    # Try to parse as JSON
                    payload[key[1:]] = json.loads(value)
                except json.JSONDecodeError:
                    payload[key[1:]] = value
            else:
                payload[key] = value
        
        # Check for form data if it's a POST
        if self.method == HttpMethod.POST:
            try:
                form_data = asyncio.run(self.form())
                for key, value in form_data.items():
                    if key.startswith('$'):
                        payload[key[1:]] = value
                    else:
                        payload[key] = value
            except:
                pass
        
        return payload
    
    def get_entity_id(self, entity_class: type) -> Optional[str]:
        """Extract entity ID from request"""
        # Check path parameters
        path_parts = self.path.split('/')
        
        # Look for entity class name in path
        class_name = entity_class.__name__.lower()
        try:
            class_index = path_parts.index(class_name)
            if class_index + 1 < len(path_parts):
                return path_parts[class_index + 1]
        except ValueError:
            pass
        
        # Check query params
        entity_id = self.query_params.get('id') or self.query_params.get('entity_id')
        if entity_id:
            return entity_id
        
        # Check form data
        try:
            form_data = asyncio.run(self.form())
            return form_data.get('id') or form_data.get('entity_id')
        except:
            pass
        
        return None

class FastHTMLResponse(WebResponse):
    """FastHTML-specific WebResponse implementation"""
    
    def __init__(self):
        super().__init__()
        self._content = None
        self._streaming_generator = None
    
    def set_content(self, content: Union[str, bytes, Dict[str, Any]]):
        """Set response content"""
        if isinstance(content, dict):
            self.set_json(content)
        elif isinstance(content, str):
            self._content = content.encode('utf-8')
            self.content_type = ContentType.HTML.value
        elif isinstance(content, bytes):
            self._content = content
        else:
            self._content = str(content).encode('utf-8')
    
    def set_json(self, data: Dict[str, Any]):
        """Set JSON response"""
        self._content = json.dumps(data).encode('utf-8')
        self.content_type = ContentType.JSON.value
    
    def set_html(self, html: str):
        """Set HTML response"""
        self._content = html.encode('utf-8')
        self.content_type = ContentType.HTML.value
    
    def set_text(self, text: str):
        """Set plain text response"""
        self._content = text.encode('utf-8')
        self.content_type = ContentType.TEXT.value
    
    def set_redirect(self, url: str, status_code: int = 302):
        """Set redirect response"""
        self.status_code = status_code
        self.set_header('Location', url)
        self._content = b''
    
    def set_stream(self, generator: AsyncIterator[str]):
        """Set streaming response"""
        self._streaming_generator = generator
        self.content_type = ContentType.STREAM.value
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')
    
    # StarModel-specific methods
    def set_sse_response(self, data: Dict[str, Any]):
        """Set Server-Sent Events response"""
        sse_data = f"data: {json.dumps(data)}\n\n"
        self.set_content(sse_data)
        self.content_type = ContentType.STREAM.value
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')
    
    def set_datastar_response(self, signals: Dict[str, Any], fragments: Optional[str] = None):
        """Set Datastar response with signals and fragments"""
        if fragments:
            # Return HTML fragments with signals
            self.set_html(fragments)
            # Add signals as a header for Datastar
            self.set_header('X-Datastar-Signals', json.dumps(signals))
        else:
            # Return just signals as SSE
            self.set_sse_response(signals)
    
    def to_starlette_response(self) -> StarletteResponse:
        """Convert to Starlette response"""
        if not FASTHTML_AVAILABLE:
            raise ImportError("FastHTML is not available")
        
        if self._streaming_generator:
            # Create streaming response
            return StreamingResponse(
                self._streaming_generator,
                status_code=self.status_code,
                headers=self.headers,
                media_type=self.content_type
            )
        else:
            # Create regular response
            response = StarletteResponse(
                content=self._content,
                status_code=self.status_code,
                headers=self.headers,
                media_type=self.content_type
            )
            
            # Add cookies
            for cookie in self.cookies:
                response.set_cookie(
                    key=cookie.name,
                    value=cookie.value,
                    max_age=cookie.max_age,
                    expires=cookie.expires,
                    path=cookie.path,
                    domain=cookie.domain,
                    secure=cookie.secure,
                    httponly=cookie.http_only,
                    samesite=cookie.same_site
                )
            
            return response

class FastHTMLAdapter(WebAdapter):
    """FastHTML web framework adapter"""
    
    def __init__(self, fasthtml_app=None, session_manager: Optional[SessionManager] = None):
        if not FASTHTML_AVAILABLE:
            raise ImportError("FastHTML is not available. Please install fasthtml to use FastHTMLAdapter.")
        
        self.app = fasthtml_app
        self.session_manager = session_manager
        self.route_registry = RouteRegistry()
        self._registered_routes = set()
    
    def create_request(self, framework_request: StarletteRequest) -> WebRequest:
        """Create WebRequest from FastHTML request"""
        # Get session data if session manager is available
        session_data = None
        if self.session_manager:
            # Extract session ID and get session data
            session_id = framework_request.cookies.get(self.session_manager.config.cookie_name)
            if session_id:
                session_data = asyncio.run(self.session_manager.get_session(session_id))
        
        return FastHTMLRequest(framework_request, session_data)
    
    def create_response(self) -> WebResponse:
        """Create WebResponse instance"""
        return FastHTMLResponse()
    
    async def send_response(self, response: WebResponse, framework_response: Any):
        """Send WebResponse using FastHTML response"""
        if isinstance(response, FastHTMLResponse):
            return response.to_starlette_response()
        else:
            # Convert generic WebResponse to FastHTML response
            fasthtml_response = FastHTMLResponse()
            fasthtml_response.status_code = response.status_code
            fasthtml_response._headers.update(response.headers)
            fasthtml_response._cookies.extend(response.cookies)
            fasthtml_response.content_type = response.content_type
            
            if hasattr(response, '_content'):
                fasthtml_response._content = response._content
            
            return fasthtml_response.to_starlette_response()
    
    def register_route(self, method: HttpMethod, path: str, handler: RouteHandler):
        """Register route with FastHTML"""
        if not self.app:
            raise ValueError("FastHTML app not provided")
        
        route_key = f"{method.value}:{path}"
        if route_key in self._registered_routes:
            return  # Already registered
        
        async def fasthtml_handler(req: StarletteRequest):
            """FastHTML route handler wrapper"""
            # Create WebRequest
            web_request = self.create_request(req)
            
            # Create context
            context = WebContext(web_request, self)
            
            # Handle request
            web_response = await handler.handle(web_request)
            
            # Convert response
            return await self.send_response(web_response, None)
        
        # Register with FastHTML app based on method
        if method == HttpMethod.GET:
            self.app.get(path)(fasthtml_handler)
        elif method == HttpMethod.POST:
            self.app.post(path)(fasthtml_handler)
        elif method == HttpMethod.PUT:
            self.app.put(path)(fasthtml_handler)
        elif method == HttpMethod.DELETE:
            self.app.delete(path)(fasthtml_handler)
        elif method == HttpMethod.PATCH:
            self.app.patch(path)(fasthtml_handler)
        
        self._registered_routes.add(route_key)
    
    def register_middleware(self, middleware: Callable):
        """Register middleware with FastHTML"""
        if not self.app:
            raise ValueError("FastHTML app not provided")
        
        # FastHTML middleware registration
        if hasattr(self.app, 'add_middleware'):
            self.app.add_middleware(middleware)
    
    def start_server(self, host: str = "localhost", port: int = 8000):
        """Start the FastHTML server"""
        if not self.app:
            raise ValueError("FastHTML app not provided")
        
        # FastHTML server startup
        if hasattr(self.app, 'run'):
            self.app.run(host=host, port=port)
        else:
            # Fallback using uvicorn if available
            try:
                import uvicorn
                uvicorn.run(self.app, host=host, port=port)
            except ImportError:
                raise ImportError("uvicorn is required to start the server")
    
    def stop_server(self):
        """Stop the FastHTML server"""
        # FastHTML doesn't have a direct stop method
        # This would need to be handled by the server runner
        pass
    
    # FastHTML-specific methods
    def register_static_files(self, path: str, directory: str):
        """Register static file serving"""
        if hasattr(self.app, 'mount'):
            from starlette.staticfiles import StaticFiles
            self.app.mount(path, StaticFiles(directory=directory), name="static")
    
    def add_exception_handler(self, exc_class: type, handler: Callable):
        """Add exception handler"""
        if hasattr(self.app, 'add_exception_handler'):
            self.app.add_exception_handler(exc_class, handler)
    
    def get_fasthtml_app(self):
        """Get the underlying FastHTML app"""
        return self.app

# Helper functions for FastHTML integration
def create_fasthtml_adapter(session_config=None) -> FastHTMLAdapter:
    """Create FastHTML adapter with default configuration"""
    if not FASTHTML_AVAILABLE:
        raise ImportError("FastHTML is not available")
    
    # Create FastHTML app
    app = FastHTML()
    
    # Create session manager if config provided
    session_manager = None
    if session_config:
        from ..session import SessionManager
        session_manager = SessionManager(session_config)
    
    return FastHTMLAdapter(app, session_manager)

def setup_datastar_integration(adapter: FastHTMLAdapter):
    """Setup Datastar integration for FastHTML adapter"""
    # Add Datastar static files and scripts
    if hasattr(adapter.app, 'hdrs'):
        # Add Datastar script to headers
        datastar_script = Script(src="https://cdn.jsdelivr.net/npm/@starfederation/datastar@latest")
        adapter.app.hdrs.append(datastar_script)

# Export main components
__all__ = [
    "FastHTMLAdapter", "FastHTMLRequest", "FastHTMLResponse",
    "create_fasthtml_adapter", "setup_datastar_integration"
]