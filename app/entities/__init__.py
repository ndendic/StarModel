"""
Demo App Entities

Domain entities for the StarModel demo application.
Each entity represents a business concept with its own behavior and persistence.
"""

from .landing import LandingEntity
from .counter import CounterEntity
from .dashboard import DashboardEntity

__all__ = [
    "LandingEntity",
    "CounterEntity", 
    "DashboardEntity"
]