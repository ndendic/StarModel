"""
Core mixins for entity functionality.

These mixins provide reusable functionality that can be mixed into
any base model (BaseModel, SQLModel, etc.) without inheritance conflicts.
"""

from .entity_mixin import EntityMixin
from .persistence_mixin import PersistenceMixin

__all__ = ["EntityMixin", "PersistenceMixin"]