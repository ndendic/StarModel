"""
StarModel Core Module

Domain layer - framework-agnostic business logic.
Contains entities, events, and signals with no external dependencies.
"""

from .entity import Entity, datastar_script
from .events import event, DatastarPayload, datastar_from_queryParams
from .signals import SignalDescriptor
from .entity_sql import SQLEntity
from .utils import singleton

__all__ = [
    "Entity", 
    "datastar_script",
    "event", 
    "DatastarPayload", 
    "datastar_from_queryParams",
    "SignalDescriptor",
    "SQLEntity",
    "singleton"
]