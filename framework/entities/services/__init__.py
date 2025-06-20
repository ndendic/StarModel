"""
Entity Services - Composition-Based Entity Capabilities

🧩 Composition Over Inheritance:
This module provides service interfaces that entities use through dependency injection
rather than inheritance. This creates cleaner separation of concerns and more testable code.

Services:
- PersistenceService: Handle entity persistence operations
- SignalService: Manage reactive signals for UI binding
- EventService: Process @event method execution
- ValidationService: Handle entity validation
- MetricsService: Track entity operation metrics
"""

from .persistence_service import PersistenceService, EntityPersistenceService
from .signal_service import SignalService, ReactiveSignalService
from .event_service import EventService, EntityEventService
from .validation_service import ValidationService, EntityValidationService
from .metrics_service import MetricsService, EntityMetricsService

__all__ = [
    # Service interfaces
    "PersistenceService", "SignalService", "EventService", 
    "ValidationService", "MetricsService",
    
    # Default implementations
    "EntityPersistenceService", "ReactiveSignalService", 
    "EntityEventService", "EntityValidationService", "EntityMetricsService"
]