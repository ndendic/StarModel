"""
Deployment Infrastructure - Application Configuration and Setup

🚀 Complete Application Orchestration:
This module provides the deployment infrastructure for StarModel applications,
handling configuration, service composition, and application lifecycle.

Components:
- StarModelConfigurator: Main application configurator
- Environment detection and configuration
- Service composition and wiring
- Application lifecycle management
"""

from .configurator import (
    StarModelConfigurator, configure_starmodel,
    configure_development_app, configure_production_app
)

__all__ = [
    "StarModelConfigurator", "configure_starmodel",
    "configure_development_app", "configure_production_app"
]