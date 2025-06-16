"""
StarModel Core Module

Domain layer - framework-agnostic business logic.
Contains entities, events, and signals with no external dependencies.
"""

from .entity import Entity, datastar_script
from .events import event, rt, DatastarPayload, datastar_from_queryParams
from .signals import SignalModelMeta, SignalDescriptor

__all__ = [
    "Entity", 
    "datastar_script",
    "event", 
    "rt",
    "DatastarPayload", 
    "datastar_from_queryParams",
    "SignalModelMeta", 
    "SignalDescriptor"
]