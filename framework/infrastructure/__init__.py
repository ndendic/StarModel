"""
Infrastructure - Technical Implementation Adapters

🔧 Pluggable Technical Components:
Contains all the technical adapters and implementations that connect
StarModel's domain logic to external systems and frameworks.

Structure:
- web/: Web framework adapters (FastHTML, FastAPI, etc.)
- storage/: Database and storage system adapters
- messaging/: Event bus and messaging system implementations
- deployment/: Configuration, setup, and deployment utilities

Example:
    from starmodel.infrastructure.web import FastHTMLAdapter
    from starmodel.infrastructure.deployment import configure_starmodel
    
    # Auto-detect web framework and configure
    app = FastHTML()
    configure_starmodel(app, entities=[User, Product, Order])
"""

# Primary exports
try:
    from .web.fasthtml_adapter import FastHTMLAdapter
    from .web.interface import WebAdapter
    from .deployment.configurator import configure_starmodel
    from .messaging.bus_implementations import InProcessBus, RedisBus
    from .storage.database_adapters import SQLiteAdapter, PostgreSQLAdapter
except ImportError:
    # Placeholders during migration
    FastHTMLAdapter = None
    WebAdapter = None
    configure_starmodel = None
    InProcessBus = None
    RedisBus = None
    SQLiteAdapter = None
    PostgreSQLAdapter = None

def configure_web(app, **config):
    """Configure web framework integration"""
    # Placeholder implementation
    pass

def auto_configure(app, entities=None, **config):
    """Auto-configure StarModel with web app"""
    # Placeholder implementation that will become configure_starmodel
    pass

__all__ = [
    "FastHTMLAdapter", "WebAdapter", "configure_starmodel",
    "InProcessBus", "RedisBus", "SQLiteAdapter", "PostgreSQLAdapter",
    "configure_web", "auto_configure"
]