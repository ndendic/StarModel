"""
Persistence Transactions - ACID Operations and Coordination

💾 Clean Transaction Management:
This module implements transaction coordination across multiple
persistence backends and domain events, ensuring data consistency
and proper rollback capabilities.

Components:
- UnitOfWork: Transaction coordination pattern
- TransactionManager: Backend-specific transaction handling
- DomainEvent: Event representation for publishing
- TransactionScope: Context manager for transactions
"""

from .unit_of_work import UnitOfWork, TransactionScope
from .domain_events import DomainEvent, EventType
from .transaction_manager import TransactionManager

__all__ = [
    "UnitOfWork", "TransactionScope", "DomainEvent", "EventType",
    "TransactionManager"
]