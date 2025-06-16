"""
StarModel Core Module

Domain layer - framework-agnostic business logic.
Contains entities, events, and signals with no external dependencies.
"""

from .entity import Entity, datastar_script
from .events import event, DatastarPayload, datastar_from_queryParams
from .signals import SignalModelMeta, SignalDescriptor

# Create a placeholder router for backward compatibility
from fasthtml.core import APIRouter
rt = APIRouter()  # This will be replaced by the FastHTML adapter pattern

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