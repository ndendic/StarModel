"""
Web Adapters - Framework-Specific Implementations

🔌 Framework Integration Layer:
This module provides concrete implementations of web adapters for
different web frameworks, enabling StarModel to work with various
web technologies while maintaining clean architecture separation.

Available Adapters:
- FastHTMLAdapter: Integration with FastHTML framework
- FastAPIAdapter: Integration with FastAPI framework (planned)
- FlaskAdapter: Integration with Flask framework (planned)
"""

from .fasthtml import FastHTMLAdapter, FastHTMLRequest, FastHTMLResponse

__all__ = [
    "FastHTMLAdapter", "FastHTMLRequest", "FastHTMLResponse"
]