"""
Entity Mixins - Composable Entity Behaviors

🧩 Modular Entity Composition:
This module provides mixins that can be composed into entities to add
specific capabilities, following the clean architecture principles.

Available Mixins:
- PersistenceMixin: Repository-based persistence operations
- SignalMixin: Reactive signal management
- EventCapable: Event handling capabilities
- ValidationMixin: Enhanced validation logic
"""

from .persistence import PersistenceMixin
from .signals import SignalMixin
from .events import EventCapable
from .validation import ValidationMixin

__all__ = [
    "PersistenceMixin", "SignalMixin", "EventCapable", "ValidationMixin"
]